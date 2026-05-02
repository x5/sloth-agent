"""SkillRouter — match user input to best available skill."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from sloth_agent.memory.skills import Skill


@dataclass
class SkillMatch:
    """Result of skill matching."""

    skill: Skill
    confidence: float  # 1.0 = exact, 0.8 = trigger, 0.5 = keyword
    match_type: str  # "exact" | "trigger" | "keyword"


class SkillRouter:
    """Match user input to the best skill.

    Matching strategy (priority order):
    1. Exact name match → confidence 1.0
    2. Trigger word match → confidence 0.8
    3. Description keyword match → confidence 0.5
    """

    def __init__(self, skills: list[Skill]):
        self._skills = skills
        self._trigger_index: dict[str, Skill] = {}
        self._keyword_index: dict[str, list[Skill]] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Build lookup indexes for fast matching."""
        for skill in self._skills:
            # Trigger words: derived from skill name + description keywords
            trigger_words = self._extract_trigger_words(skill)
            for word in trigger_words:
                if word not in self._trigger_index:
                    self._trigger_index[word] = skill

            # Keyword index: split description into words
            keywords = self._tokenize(skill.description)
            for kw in keywords:
                if kw not in self._keyword_index:
                    self._keyword_index[kw] = []
                if skill not in self._keyword_index[kw]:
                    self._keyword_index[kw].append(skill)

    def match(self, user_input: str) -> SkillMatch | None:
        """Find the best matching skill for user input.

        Returns None if no match found at any confidence level.
        """
        # 1. Exact name match
        for skill in self._skills:
            if skill.id.lower() == user_input.strip().lower():
                return SkillMatch(skill=skill, confidence=1.0, match_type="exact")
            if skill.name.lower() == user_input.strip().lower():
                return SkillMatch(skill=skill, confidence=1.0, match_type="exact")

        # 2. Trigger word match
        input_lower = user_input.lower()
        best_trigger: SkillMatch | None = None
        for word, skill in self._trigger_index.items():
            if word in input_lower:
                # Longer word = more specific match
                score = len(word)
                if best_trigger is None or score > best_trigger.skill.name.count(" "):
                    best_trigger = SkillMatch(
                        skill=skill, confidence=0.8, match_type="trigger",
                    )
        if best_trigger:
            return best_trigger

        # 3. Description keyword match (FTS-style)
        input_tokens = self._tokenize(input_lower)
        best_keyword: tuple[Skill, int] | None = None
        for token in input_tokens:
            if token in self._keyword_index:
                for skill in self._keyword_index[token]:
                    count = best_keyword[1] if best_keyword else 0
                    if count < 1:  # First match wins at this level
                        best_keyword = (skill, 1)
        if best_keyword:
            return SkillMatch(
                skill=best_keyword[0], confidence=0.5, match_type="keyword",
            )

        return None

    def match_all(self, user_input: str, min_confidence: float = 0.5) -> list[SkillMatch]:
        """Return all matches above minimum confidence, sorted by confidence."""
        results = []
        seen_ids: set[str] = set()

        exact = self.match(user_input)
        if exact and exact.confidence >= min_confidence:
            results.append(exact)
            seen_ids.add(exact.skill.id)

        if min_confidence <= 0.8:
            input_lower = user_input.lower()
            for word, skill in self._trigger_index.items():
                if word in input_lower and skill.id not in seen_ids:
                    results.append(
                        SkillMatch(skill=skill, confidence=0.8, match_type="trigger"),
                    )
                    seen_ids.add(skill.id)

        if min_confidence <= 0.5:
            input_tokens = self._tokenize(user_input.lower())
            for token in input_tokens:
                if token in self._keyword_index:
                    for skill in self._keyword_index[token]:
                        if skill.id not in seen_ids:
                            results.append(
                                SkillMatch(
                                    skill=skill, confidence=0.5, match_type="keyword",
                                ),
                            )
                            seen_ids.add(skill.id)

        results.sort(key=lambda m: m.confidence, reverse=True)
        return results

    def search(self, query: str) -> list[Skill]:
        """Search skills by query (case-insensitive substring)."""
        query_lower = query.lower()
        results = []
        for skill in self._skills:
            if (
                query_lower in skill.name.lower()
                or query_lower in skill.description.lower()
                or query_lower in skill.id.lower()
            ):
                results.append(skill)
        return results

    @staticmethod
    def _extract_trigger_words(skill: Skill) -> list[str]:
        """Extract trigger words from a skill."""
        words = []
        # Skill name parts (e.g., "test-driven-development" → ["test", "driven", "development"])
        words.extend(re.split(r"[-_\s]+", skill.id.lower()))
        # Keywords from description
        words.extend(SkillRouter._tokenize(skill.description.lower()))
        # Remove stopwords and short words
        stopwords = {"the", "a", "an", "is", "to", "for", "of", "and", "or", "in", "on", "with"}
        return [w for w in words if w not in stopwords and len(w) > 2]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Split text into lowercase tokens."""
        return [w for w in re.findall(r"[a-z0-9\u4e00-\u9fff]+", text.lower()) if len(w) > 1]
