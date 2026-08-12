import json
from pathlib import Path

POSTS = [
    {
        "title": "The Secret Life of Red Foxes",
        "body": "Red foxes are among the most adaptable mammals on Earth, thriving in forests, grasslands, and even busy city neighborhoods. Their russet coats, sharp senses, and bushy tails make them one of the most recognizable wild animals to spot.",
    },
    {
        "title": "How Wolf Packs Hunt Together",
        "body": "A wolf pack hunts as a single coordinated unit, using teamwork and communication to take down prey far larger than any individual wolf. Understanding their howls, body language, and strategy reveals why they are such successful predators.",
    },
    {
        "title": "Why Dogs Are Man's Best Friend",
        "body": "Dogs have lived alongside humans for thousands of years, evolving into loyal companions that understand our moods and commands. From herding sheep to fetching a favorite toy, no other animal shares such a close bond with people.",
    },
    {
        "title": "Bears: Gentle Giants of the Wild",
        "body": "Despite their fearsome reputation, most bears prefer to avoid humans and spend their days foraging for berries, fish, and roots. These powerful animals play a vital role in keeping forest ecosystems healthy and balanced.",
    },
    {
        "title": "The Graceful World of Deer",
        "body": "Deer are elegant creatures known for their graceful leaps and gentle browsing through woodland clearings. Whether it is the majestic antlers of a stag or the cautious steps of a doe, they bring a quiet beauty to the forest.",
    },
    {
        "title": "Brewing a Better Cup of Coffee at Home",
        "body": "Great coffee at home comes down to fresh beans, the right water temperature, and a consistent grind size. A simple pour-over setup can rival your favorite cafe and save you money in the long run.",
    },
    {
        "title": "Hiking Gear Review: The Best Trail Boots of the Year",
        "body": "A good pair of trail boots can make or break a long hike, offering grip, support, and comfort across rough terrain. We tested this year's top models to find which ones keep your feet happy on the mountain.",
    },
]


def main() -> None:
    out_path = Path("data/posts.json")
    out_path.write_text(json.dumps(POSTS, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(POSTS)} placeholder posts to {out_path}")


if __name__ == "__main__":
    main()
