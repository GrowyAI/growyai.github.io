"""Add concrete-noun emoji hints to knowledge items.

Only recognizable things get an emoji (world map -> 🗺️, dinosaur -> 🦕).
Abstract skills, actions, and broad categories are intentionally left empty.
"""

import collections
import json
import os
import re
import shutil

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SOURCE = os.path.join(DATA, "knowledge.json")
BACKUP = os.path.join(DATA, "knowledge-before-emojis.json")
MAX_EMOJI = 2
# Emojis appearing at or above this many times are dropped everywhere;
# repeated icons add noise rather than information.
MAX_FREQUENCY = 100

# Each entry: emoji -> regex fragments for concrete nouns.
# Longer/more specific phrases win because patterns are sorted by length.
RULES = [
    ("🗺️", [r"world\s+map", r"map", r"atlas", r"geography"]),
    ("🌍", [r"planet\s+earth", r"the\s+earth", r"earth", r"globe"]),
    ("🌌", [r"universe", r"galax(?:y|ies)"]),
    ("🇺🇸", [r"united\s+states", r"u\.?s\.?a\.?"]),
    ("🇨🇳", [r"china", r"people'?s\s+republic\s+of\s+china"]),
    ("🇯🇵", [r"japan"]),
    ("🇮🇳", [r"india"]),
    ("🇫🇷", [r"france", r"french"]),
    ("🇬🇧", [r"great\s+britain", r"united\s+kingdom", r"britain", r"england"]),
    ("🇩🇪", [r"germany", r"german"]),
    ("🇮🇹", [r"italy", r"italian"]),
    ("🇪🇸", [r"spain", r"spanish"]),
    ("🇲🇽", [r"mexico", r"mexican"]),
    ("🇨🇦", [r"canada", r"canadian"]),
    ("🇷🇺", [r"soviet\s+union", r"soviet", r"russia", r"russian"]),
    ("🇦🇺", [r"australia"]),
    ("🇧🇷", [r"brazil"]),
    ("🇪🇬", [r"egypt", r"egyptian"]),
    ("🇬🇷", [r"greece", r"greek"]),
    ("🇰🇷", [r"korea", r"korean"]),
    ("🇻🇳", [r"vietnam"]),
    ("🇵🇦", [r"panama"]),
    ("🇬🇹", [r"guatemala"]),
    ("🇭🇹", [r"haiti"]),
    ("🇩🇴", [r"dominican\s+republic"]),
    ("🇿🇦", [r"south\s+africa"]),
    ("🗽", [r"new\s+york", r"statue\s+of\s+liberty"]),
    ("🗼", [r"paris"]),
    ("🏙️", [r"london", r"city", r"urban"]),
    ("🏞️", [r"river", r"lake", r"waterfall", r"nile"]),
    ("⛰️", [r"mountains?", r"hills?"]),
    ("🏜️", [r"deserts?", r"canyons?", r"drought"]),
    ("🏝️", [r"islands?"]),
    ("🌲", [r"forests?", r"woods"]),
    ("🌊", [r"oceans?", r"pacific", r"atlantic", r"mediterranean",
           r"tides?", r"floods?", r"ocean\s+waves?"]),
    ("🌋", [r"volcano(?:es)?", r"volcanic", r"earthquakes?"]),
    ("🧊", [r"glaciers?", r"icebergs?"]),
    ("☀️", [r"sun", r"solar\s+energy", r"sunlight"]),
    ("🌙", [r"moon", r"lunar"]),
    ("⭐", [r"stars?", r"constellations?"]),
    ("🪐", [r"solar\s+system", r"planets?", r"orbits?", r"astronomy"]),
    ("🔭", [r"telescopes?"]),
    ("🚀", [r"rockets?", r"spacecraft", r"astronauts?", r"spaceflight", r"satellites?"]),
    ("🛰️", [r"satellites?"]),
    ("💧", [r"water\s+cycle", r"water", r"rain", r"droplets?"]),
    ("☁️", [r"clouds?"]),
    ("❄️", [r"snow", r"freezing", r"frozen"]),
    ("🌬️", [r"wind"]),
    ("🌪️", [r"tornado(?:es)?", r"hurricanes?", r"typhoons?"]),
    ("⛈️", [r"thunder", r"lightning", r"storms?"]),
    ("🌈", [r"rainbows?"]),
    ("🔥", [r"fire", r"flames?"]),
    ("🌡️", [r"temperature", r"thermometer", r"thermal\s+energy", r"heating", r"cooling"]),
    ("💡", [r"light\s+waves?", r"light\s+bulb", r"light", r"rays?", r"shadows?",
           r"prisms?", r"reflection", r"refraction"]),
    ("🔊", [r"sound\s+waves?", r"sounds?", r"vibrations?", r"echo"]),
    ("🧲", [r"magnets?", r"magnetism", r"magnetic"]),
    ("⚡", [r"electricity", r"electric\s+circuits?", r"circuits?", r"voltage", r"lightning"]),
    ("🔋", [r"batteries", r"battery"]),
    ("⚙️", [r"simple\s+machines?", r"levers?", r"pulleys?", r"gears?", r"engines?",
           r"machines?", r"friction", r"motion"]),
    ("⚖️", [r"gravity", r"balances?", r"scales?"]),
    ("🔬", [r"microscopes?", r"cells?", r"cellular", r"organism", r"laborator(?:y|ies)"]),
    ("🦠", [r"bacteria", r"viruses?", r"microbes?"]),
    ("🧬", [r"dna", r"genes?", r"genetics", r"heredity", r"chromosomes?"]),
    ("⚗️", [r"atoms?", r"molecules?", r"chemical", r"chemistry", r"chemical\s+reactions?"]),
    ("☢️", [r"atomic\s+bomb", r"atomic\s+age", r"nuclear", r"radiation"]),
    ("🧪", [r"experiments?", r"hypotheses?", r"hypothesis", r"scientific\s+method"]),
    ("♻️", [r"recycling", r"recycle", r"conservation", r"natural\s+resources?"]),
    ("🛢️", [r"oil", r"petroleum", r"fossil\s+fuels?"]),
    ("⛏️", [r"mining", r"miners?", r"coal", r"gold\s+rush"]),
    ("💻", [r"computers?", r"digital\s+sources?", r"internet"]),
    ("🌐", [r"internet", r"world\s+wide\s+web"]),
    ("📻", [r"radio"]),
    ("📺", [r"television", r"tv"]),
    ("☎️", [r"telephones?", r"phones?"]),

    ("🦕", [r"dinosaurs?", r"tyrannosaurus", r"t\-?rex"]),
    ("🦖", [r"tyrannosaurus", r"t\-?rex"]),
    ("🦋", [r"butterflies", r"butterfly", r"caterpillars?", r"moths?"]),
    ("🐝", [r"bees?", r"honeybees?", r"hives?"]),
    ("🐜", [r"ants?"]),
    ("🕷️", [r"spiders?"]),
    ("🪱", [r"worms?"]),
    ("🐸", [r"frogs?", r"tadpoles?"]),
    ("🐍", [r"snakes?"]),
    ("🐢", [r"turtles?", r"tortoises?"]),
    ("🦎", [r"lizards?"]),
    ("🐊", [r"crocodiles?", r"alligators?"]),
    ("🐦", [r"birds?", r"avian"]),
    ("🦅", [r"eagles?"]),
    ("🦉", [r"owls?"]),
    ("🐔", [r"chickens?", r"hens?", r"roosters?"]),
    ("🦆", [r"ducks?", r"geese", r"goose"]),
    ("🐟", [r"fish", r"fishes"]),
    ("🦈", [r"sharks?"]),
    ("🐋", [r"whales?"]),
    ("🐬", [r"dolphins?"]),
    ("🐙", [r"octopuses?", r"octopi"]),
    ("🦑", [r"squids?"]),
    ("🐌", [r"snails?"]),
    ("🪲", [r"beetles?"]),
    ("🦗", [r"crickets?"]),
    ("🦇", [r"bats?"]),
    ("🐘", [r"elephants?"]),
    ("🦏", [r"rhinoceros", r"rhinos?"]),
    ("🦒", [r"giraffes?"]),
    ("🦌", [r"deer"]),
    ("🐴", [r"horses?", r"ponies?", r"pony"]),
    ("🦓", [r"zebras?"]),
    ("🐄", [r"cows?", r"bulls?", r"oxen"]),
    ("🐷", [r"pigs?", r"piglets?"]),
    ("🐑", [r"sheep", r"lambs?"]),
    ("🐐", [r"goats?"]),
    ("🐶", [r"dogs?", r"puppies?", r"puppy"]),
    ("🐱", [r"cats?", r"kittens?", r"kitten"]),
    ("🐰", [r"rabbits?", r"bunnies?"]),
    ("🐭", [r"mice", r"mouse", r"rats?"]),
    ("🐹", [r"hamsters?"]),
    ("🐒", [r"monkeys?", r"apes?"]),
    ("🦍", [r"gorillas?"]),
    ("🐻", [r"bears?"]),
    ("🦁", [r"lions?"]),
    ("🐯", [r"tigers?"]),
    ("🐺", [r"wolves?", r"wolf"]),
    ("🦊", [r"foxes?", r"fox"]),
    ("🐫", [r"camels?"]),
    ("🐧", [r"penguins?"]),
    ("🦩", [r"flamingos?"]),
    ("🌱", [r"seeds?", r"seedlings?", r"plants?", r"sprouts?", r"photosynthesis"]),
    ("🌳", [r"trees?"]),
    ("🍃", [r"leaves", r"leaf"]),
    ("🌸", [r"flowers?", r"blossoms?"]),
    ("🌾", [r"crops?", r"wheat", r"corn", r"farms?", r"farmers?", r"agriculture", r"harvests?"]),

    ("🫀", [r"hearts?"]),
    ("🧠", [r"brains?", r"nervous\s+system"]),
    ("🫁", [r"lungs?", r"respiration"]),
    ("👁️", [r"eyes?", r"vision", r"sight"]),
    ("👂", [r"ears?", r"hearing"]),
    ("👃", [r"noses?", r"smell"]),
    ("👅", [r"tongues?", r"taste"]),
    ("🖐️", [r"hands?", r"touch"]),
    ("🦴", [r"bones?", r"skeletons?", r"fossils?"]),
    ("🩸", [r"blood"]),
    ("🦷", [r"teeth", r"tooth"]),
    ("🩺", [r"doctors?", r"nurses?", r"stethoscopes?"]),
    ("🏥", [r"hospitals?"]),
    ("💊", [r"medicines?", r"vaccines?", r"vitamins?"]),

    ("🍎", [r"apples?", r"fruit"]),
    ("🍌", [r"bananas?"]),
    ("🍊", [r"oranges?"]),
    ("🍇", [r"grapes?"]),
    ("🍓", [r"strawberries", r"strawberry"]),
    ("🍉", [r"watermelons?"]),
    ("🥕", [r"carrots?"]),
    ("🥔", [r"potatoes?", r"potato"]),
    ("🍅", [r"tomatoes?", r"tomato"]),
    ("🥬", [r"lettuce", r"vegetables?"]),
    ("🍞", [r"bread", r"toast"]),
    ("🥛", [r"milk"]),
    ("🧀", [r"cheese"]),
    ("🥚", [r"eggs?", r"egg"]),
    ("🍚", [r"rice"]),
    ("🍝", [r"pasta", r"spaghetti"]),
    ("🍕", [r"pizza"]),
    ("🍪", [r"cookies?", r"biscuits?"]),
    ("🍦", [r"ice\s+cream"]),
    ("🍰", [r"cakes?", r"cupcakes?"]),
    ("🍯", [r"honey"]),
    ("🍽️", [r"meals?", r"breakfast", r"lunch", r"dinner"]),

    ("🎹", [r"pianos?"]),
    ("🎸", [r"guitars?"]),
    ("🎻", [r"violins?", r"cellos?", r"string\s+instruments?"]),
    ("🥁", [r"drums?", r"percussion"]),
    ("🎺", [r"trumpets?", r"brass\s+instruments?"]),
    ("🪈", [r"flutes?", r"recorders?"]),
    ("🎤", [r"singing", r"sings?", r"singers?", r"choirs?", r"choruses?", r"chorus", r"voices?"]),
    ("🎧", [r"headphones?", r"audiences?", r"audience"]),
    ("🎵", [r"melodies?", r"rhythms?", r"beats?", r"tempos?", r"tunes?"]),
    ("🎼", [r"sheet\s+music", r"musical\s+notation", r"treble\s+clef", r"staff", r"scores?"]),
    ("🎭", [r"drama", r"theater", r"theatre", r"playwrights?"]),
    ("💬", [r"dialogues?", r"conversations?"]),

    ("🎨", [r"paintings?", r"paints?", r"palettes?", r"colors?", r"colours?",
           r"drawings?", r"sketches?", r"artists?", r"portraits?", r"murals?"]),
    ("🖌️", [r"brushes?"]),
    ("🗿", [r"sculptures?", r"sculpting", r"statues?"]),
    ("🏺", [r"pottery", r"ceramics?", r"vases?", r"artifacts?", r"ancient\s+civilizations?"]),
    ("🏛️", [r"architecture", r"cathedrals?", r"castles?", r"ruins",
           r"capitol", r"constitution", r"courts?", r"senate", r"congress"]),
    ("🖼️", [r"museums?", r"galleries?", r"gallery", r"exhibits?"]),
    ("📷", [r"cameras?", r"photographs?", r"photos?", r"photography"]),
    ("✂️", [r"scissors?"]),
    ("🧵", [r"thread", r"weaving"]),
    ("🧶", [r"yarn"]),
    ("🪡", [r"needles?"]),

    ("📖", [r"books?", r"novels?", r"fairy\s+tales?", r"fables?",
           r"myths?", r"legends?"]),
    ("📚", [r"libraries?", r"librarians?"]),
    ("📔", [r"journals?", r"diaries?"]),
    ("📄", [r"paper", r"essays?"]),
    ("📰", [r"newspapers?", r"magazines?", r"articles?"]),
    ("💌", [r"letters?", r"postcards?"]),
    ("📜", [r"declarations?", r"speeches?", r"manuscripts?", r"scrolls?", r"treaties?", r"documents?"]),
    ("✏️", [r"pencils?"]),
    ("🖊️", [r"pens?"]),
    ("🖍️", [r"crayons?"]),

    ("🗳️", [r"elections?", r"voting", r"votes?", r"ballots?"]),
    ("👑", [r"kings?", r"queens?", r"emperors?", r"monarchs?",
           r"princes?", r"princesses?"]),
    ("⚔️", [r"world\s+wars?", r"civil\s+war", r"revolutionary\s+war", r"war\s+of\s+1812",
           r"vietnam\s+war", r"battles?", r"weapons?"]),
    ("🪖", [r"soldiers?", r"armies?", r"army"]),
    ("⛓️", [r"slavery", r"slaves?", r"enslaved\s+people", r"slave\s+trade"]),
    ("✊", [r"civil\s+rights", r"protests?", r"reformers?", r"social\s+movements?"]),
    ("🕊️", [r"peace", r"abolition"]),
    ("🧭", [r"explorers?", r"exploration", r"exploring", r"pioneers?", r"westward",
           r"migrating", r"migration", r"northwest\s+passage"]),
    ("🚢", [r"ships?", r"boats?", r"sailing", r"voyages?"]),
    ("🚂", [r"trains?", r"railroads?", r"railways?", r"industrialization", r"factories?", r"steam"]),
    ("🏭", [r"factories?", r"industrial\s+revolution"]),
    ("🚜", [r"tractors?", r"farming", r"farm\s+equipment"]),
    ("📉", [r"great\s+depression", r"depression\s+era", r"economic\s+decline"]),
    ("📈", [r"trade", r"economy", r"capitalism", r"business", r"markets?"]),
    ("🎖️", [r"napoleon", r"generals?"]),
    ("💣", [r"bombs?"]),
    ("⛪", [r"churches?", r"christianity", r"christians?", r"the\s+church"]),
    ("🕌", [r"islam", r"muslims?", r"mosques?"]),
    ("🕍", [r"judaism", r"jews?", r"jewish", r"synagogues?"]),
    ("🪷", [r"buddhism", r"hinduism"]),
    ("🎉", [r"holidays?", r"celebrations?", r"festivals?", r"independence\s+day", r"july\s+4"]),

    ("🔢", [r"counting", r"digits?", r"numerals?", r"cardinality",
           r"place\s+value", r"whole\s+numbers?", r"integers?", r"rational\s+numbers?"]),
    ("➕", [r"addition", r"adding", r"adds?", r"sums?"]),
    ("➖", [r"subtraction", r"subtracting", r"subtract", r"differences?"]),
    ("✖️", [r"multiplication", r"multiplying", r"multiply", r"products?"]),
    ("➗", [r"division", r"dividing", r"divide", r"fractions?", r"ratios?", r"proportions?",
           r"decimals?", r"percents?"]),
    ("🧮", [r"equations?", r"algebra", r"linear\s+functions?", r"quadratic\s+functions?",
           r"variables?", r"calculations?"]),
    ("📐", [r"geometry", r"shapes?", r"triangles?", r"squares?", r"rectangles?",
           r"polygons?", r"angles?", r"symmetry"]),
    ("⭕", [r"circles?"]),
    ("🔺", [r"triangles?"]),
    ("🟦", [r"squares?"]),
    ("📏", [r"measurement", r"measuring", r"length", r"width", r"height",
           r"weight", r"mass", r"rulers?", r"inches", r"meters?", r"centimeters?"]),
    ("🕒", [r"clocks?", r"hours?", r"minutes?"]),
    ("🗓️", [r"calendars?", r"dates?", r"months?"]),
    ("💰", [r"money", r"prices?", r"costs?"]),
    ("🪙", [r"coins?"]),
    ("💵", [r"dollars?", r"cents?"]),
    ("📊", [r"graphs?", r"charts?", r"data", r"statistics", r"probability", r"tables?"]),
    ("🧩", [r"patterns?", r"puzzles?"]),
    ("🎲", [r"dice", r"probability"]),

    # Concrete actions with a clear visual emoji
    ("🙋", [r"raise\s+(?:one'?s\s+|your\s+|their\s+)?hands?", r"raising\s+(?:one'?s\s+|your\s+|their\s+)?hands?",
           r"hands?\s+up"]),
    ("👏", [r"clap(?:s|ping)?"]),
    ("👋", [r"wav(?:e|ing)\s+(?:goodbye|hello|hi)", r"wave\s+goodbye", r"waving\s+goodbye"]),
    ("🤝", [r"shake\s+hands?", r"shaking\s+hands?", r"handshakes?"]),
    ("🗣️", [r"speaks?", r"speaking", r"talks?", r"talking"]),
    ("👉", [r"points?\s+to", r"pointing\s+to"]),
    ("👀", [r"looks?\s+at", r"looking\s+at"]),
    ("🏃", [r"run(?:s)?(?!\s+(?:a|an|the|for|business|company|government|organization)|-)",
           r"ran"]),
    ("🚶", [r"walks?", r"walking"]),
    ("🤸", [r"jumps?", r"jumping", r"hops?", r"hopping", r"skips?", r"skipping"]),
    ("🕺", [r"danc(?:e|es|ing)"]),
    ("🧍", [r"stands?", r"standing"]),
    ("🪑", [r"sits?", r"sitting"]),
    ("🛌", [r"sleeps?", r"sleeping"]),

    ("🧸", [r"teddy\s+bears?", r"toys?"]),
    ("⚽", [r"soccer", r"balls?"]),
    ("🏀", [r"basketballs?"]),
    ("🧱", [r"blocks?"]),
    ("🎈", [r"balloons?"]),
    ("🪁", [r"kites?"]),
    ("🚲", [r"bicycles?", r"bikes?"]),
    ("🚗", [r"cars?"]),
    ("🚌", [r"buses?", r"bus"]),
    ("✈️", [r"airplanes?", r"planes?", r"aircraft"]),
    ("👟", [r"shoes?", r"sneakers?"]),
    ("👕", [r"shirts?", r"clothes", r"clothing", r"dresses?"]),
    ("🧢", [r"hats?", r"caps?"]),
    ("🪥", [r"toothbrushes?"]),
    ("🧼", [r"soap"]),
    ("🍼", [r"baby\s+bottles?", r"bottles?"]),
    ("🛏️", [r"beds?"]),
    ("🪑", [r"chairs?"]),
    ("🥄", [r"spoons?"]),
    ("🍴", [r"forks?"]),
    ("🥣", [r"bowls?"]),
    ("🧺", [r"baskets?"]),
    ("🎒", [r"backpacks?"]),
    ("👶", [r"babies?", r"baby", r"infants?", r"toddlers?"]),
]


def _compile():
    compiled = []
    for emoji, terms in RULES:
        for term in terms:
            # Lookarounds instead of \b so terms ending in punctuation still match.
            pattern = re.compile(r"(?<![A-Za-z])(?:%s)(?![A-Za-z])" % term, re.IGNORECASE)
            priority = len(re.sub(r"[\\()?:|+\-.]", "", term))
            compiled.append((priority, pattern, emoji))
    compiled.sort(key=lambda x: -x[0])
    return [(p, e) for _, p, e in compiled]


COMPILED = _compile()


def pick_emojis(item):
    if item.get("type") == "note":
        return []
    parts = [
        item.get("en", ""),
        " ".join(item.get("details", []) or []),
    ]
    hay = " ".join(str(p) for p in parts)
    # Removing document boilerplate prevents topic-wide false matches such as
    # "Core Knowledge Sequence" triggering the puzzle emoji.
    hay = re.sub(r"Core\s+Knowledge\s+Sequence|Critical\s+Skill|Bull\s+Run", " ", hay, flags=re.IGNORECASE)
    out = []
    for pattern, emoji in COMPILED:
        if emoji in out:
            continue
        if pattern.search(hay):
            out.append(emoji)
            if len(out) >= MAX_EMOJI:
                break
    return out


def main():
    with open(SOURCE, encoding="utf-8") as f:
        data = json.load(f)
    if not os.path.exists(BACKUP):
        shutil.copyfile(SOURCE, BACKUP)
    for item in data["items"]:
        item["emojis"] = pick_emojis(item)

    raw_count = collections.Counter(e for i in data["items"] for e in i["emojis"])
    banned = {e for e, n in raw_count.items() if n >= MAX_FREQUENCY}
    if banned:
        for item in data["items"]:
            item["emojis"] = [e for e in item["emojis"] if e not in banned]

    with open(SOURCE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    count = collections.Counter()
    by_subject = collections.Counter()
    emoji_count = collections.Counter()
    for item in data["items"]:
        if item["emojis"]:
            count["with"] += 1
            by_subject[item["subject"]] += 1
            emoji_count.update(item["emojis"])
        else:
            count["without"] += 1
    print("emoji coverage:", dict(count), "of", len(data["items"]))
    print("banned by frequency:", sorted(banned), "threshold", MAX_FREQUENCY)
    print("top emoji:", emoji_count.most_common(15))
    for subject, n in by_subject.most_common():
        print("  %-45s %d" % (subject, n))


if __name__ == "__main__":
    main()
