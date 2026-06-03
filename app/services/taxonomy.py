"""Topic taxonomy for the blog.

The blog has 250+ posts but no stored category field. Rather than a DB
migration, topics are derived deterministically from each post's slug and
title by ordered keyword rules. This keeps the taxonomy version-controlled,
testable, and identical in every environment, and lets topic hub pages group
the corpus so no post is a crawl orphan.

Assignment is single-primary: categories are evaluated in PRIORITY order and
the first whose keyword matches wins. Order therefore encodes precedence for
posts that could fit several topics (e.g. "mantra-meditation-athletes" is a
technique, not a sport). LIFE is the catch-all and must stay last.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    key: str          # URL slug: /blog/topics/<key>
    title: str        # Human label
    blurb: str        # One-line description for hub header + topics index
    keywords: tuple[str, ...]  # matched as substrings of "slug title".lower()


# Priority order matters — first match wins. LIFE is the catch-all (last).
TOPICS: tuple[Topic, ...] = (
    Topic(
        "by-sport",
        "Meditation by Sport",
        "Sport-specific mental training — the same practice, tuned to the demands of your game.",
        (
            "for-baseball", "for-basketball", "for-golfers", "for-climbers", "climbing-",
            "for-cyclists", "for-runners", "for-soccer", "for-swimmers", "for-swimming",
            "for-tennis", "for-track-field", "for-triathletes", "for-volleyball",
            "for-winter-sports", "for-crossfit", "for-powerlifting", "for-rowing",
            "for-gymnastics", "for-pickleball", "combat-sports", "for-esports",
            "esports-mental", "surfing-", "zen-sports",
        ),
    ),
    Topic(
        "teams-coaching",
        "Teams & Coaching",
        "Bringing mental training to a group — for coaches, captains, parents, and the people around the athlete.",
        (
            "team-", "-team", "coach", "pre-game-team", "parents-guide",
            "working-with-sports-psychologist", "teammate", "student-athlete-balance",
            "mentally-tough-team", "mental-skills-coaching", "mental-skills-program",
        ),
    ),
    Topic(
        "traditions",
        "Traditions & Philosophy",
        "Where these practices come from — the lineages and philosophies behind modern mental training.",
        (
            "buddhist", "buddhism", "christian", "hindu", "jewish", "sufi", "taoist",
            "tibetan", "zen", "zazen", "theravada", "mahayana", "transcendental",
            "samurai", "stoic", "lojong", "secular-vs-traditional",
            "concentration-vs-insight", "dark-night",
        ),
    ),
    Topic(
        "techniques",
        "Techniques & Practices",
        "How to actually do it — specific meditation and breathing methods, step by step.",
        (
            "box-breathing", "4-7-8", "breath-counting", "breath-hold", "breathwork",
            "physiological-sigh", "yogic-breath", "pranayama", "body-scan",
            "progressive-muscle", "walking-meditation", "mantra", "metta",
            "loving-kindness", "noting", "mahasi", "open-awareness", "choiceless",
            "non-dual", "self-inquiry", "trataka", "tonglen", "yoga-nidra",
            "autogenic", "vipassana", "jhana", "stages-of-insight", "wim-hof",
            "chakra", "eyes-open", "postures", "nsdr-non-sleep",
        ),
    ),
    Topic(
        "science",
        "The Science",
        "What the research shows — the neuroscience and physiology of meditation and performance.",
        (
            "bdnf", "neuro", "brain", "default-mode", "endorphin", "epigenetic",
            "cortisol", "testosterone", "hrv", "heart-rate-variability", "biomarker",
            "immune", "longevity", "gut-brain", "nutrition-gut", "proprioception",
            "reaction-time", "research-athletes", "50-studies", "relaxation-response",
            "pain-science", "habit-formation-science", "long-term-meditator",
        ),
    ),
    Topic(
        "recovery-injury",
        "Recovery & Injury",
        "The mental side of getting hurt, healing, and coming back — plus sleep and physical recovery.",
        (
            "injur", "surgery", "concussion", "reinjury", "chronic-pain",
            "playing-through-pain", "mental-game-injury", "act-therapy", "recovery",
            "returning-to-sport", "return-to-sport", "sleep", "insomnia", "nsdr",
            "vagus", "cold-exposure", "inflammation", "wim-hof", "comeback",
        ),
    ),
    Topic(
        "challenges",
        "Common Challenges",
        "When practice gets hard — troubleshooting the obstacles every meditator hits.",
        (
            "am-i-doing-this-right", "boredom", "racing-thoughts", "restlessness",
            "falling-asleep", "physical-discomfort", "headache", "harder-some-days",
            "makes-you-feel-worse", "causes-anxiety", "emotional-releases",
            "dissociation", "lost-motivation", "plateau", "when-meditation-not-enough",
        ),
    ),
    Topic(
        "getting-started",
        "Getting Started",
        "New to meditation? Start here — the practical questions and tools for building a practice.",
        (
            "best-time", "how-long", "daily-meditation-habit", "habit", "meditation-space",
            "creating-meditation-space", "guided-vs-unguided", "how-to-know",
            "signs-meditation-progress", "myths", "finding-meditation-teacher",
            "return-to-meditation-after-break", "when-increase", "short-vs-long",
            "timer", "morning-vs-evening", "tracking-meditation", "without-apps",
            "home-meditation-retreat", "free-vs-paid", "minimalist", "meditation-apps",
            "mbsr", "short-on-time", "while-traveling", "how-to-meditate",
        ),
    ),
    Topic(
        "performance",
        "Performance Psychology",
        "Mind under pressure — focus, flow, slumps, and the mental game of competition.",
        (
            "pressure", "clutch", "slump", "flow-state", "competition", "playoff",
            "second-half", "contract-year", "between-match", "visualization",
            "imagery", "pettlep", "mental-warmup", "mental-rehearsal", "fear-of-success",
            "imposter", "perfectionism", "anger", "off-season", "periodizing",
            "why-athletes", "attention-economy", "focus-training", "late-bloomer",
            "amateur-to-pro", "undersized", "competition-day", "warmup-before",
            "pre-game", "morning-routines",
        ),
    ),
    Topic(
        "life",
        "For Your Life",
        "Meditation for who you are and what you're going through — every profession, life stage, and transition.",
        (),  # catch-all — no keywords; everything unmatched lands here
    ),
)

# Audience/life keywords are documented here for readers but not needed for
# routing, since LIFE is the terminal catch-all. Kept empty above on purpose.

_TOPIC_BY_KEY = {t.key: t for t in TOPICS}
LIFE_KEY = "life"


def topic_for(slug: str, title: str = "") -> str:
    """Return the primary topic key for a post (first matching rule wins)."""
    hay = f"{slug} {title}".lower()
    for topic in TOPICS:
        if any(kw in hay for kw in topic.keywords):
            return topic.key
    return LIFE_KEY


def get_topic(key: str) -> Topic | None:
    return _TOPIC_BY_KEY.get(key)


def all_topics() -> tuple[Topic, ...]:
    return TOPICS
