import holidays
from datetime import datetime
from typing import List, Optional
import re
from services.llm_service import get_llm_service

class CalendarService:
    def __init__(self):
        self.llm_service = get_llm_service()
        self.indian_holidays = holidays.India()

    async def generate_calendar(
        self,
        month: str,
        year: int,
        niche: str,
        content_goals: str,
        content_formats: List[str],
        posts_per_month: int,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Generates a content calendar for a specific month focusing on dynamic Indian festivals and niche.
        """
        # Get holidays for the specific month/year
        month_num = datetime.strptime(month, "%B").month
        holiday_list = []
        for date, name in self.indian_holidays.items():
            if date.year == year and date.month == month_num:
                holiday_list.append(f"{name} ({date.day} {month})")
        
        festival_str = ", ".join(holiday_list) if holiday_list else "No major holidays"
        
        format_str = ", ".join(content_formats)
        prompt = f"""
        Create a detailed monthly content calendar for {month} {year} for a creator in the '{niche}' niche.
        
        **Context:**
        - Target Audience: Indian market
        - Key Festivals/Events: {festival_str}
        - Content Goal: {content_goals}
        - Allowed Content Formats: {format_str}
        - Number of Posts Required: {posts_per_month}
        
        **Output Requirement:**
        Strictly return a clean Markdown table with the following columns:
        | Post # | Date | Content Pillar | Topic | Format | Caption Hook |
        
        **Guidelines:**
        - Return exactly {posts_per_month} data rows (excluding header and separator rows).
        - Use only these formats in the Format column: {format_str}.
        - Spread posts realistically across the month, and include multiple posts on the same day when needed.
        - Integrate the festivals naturally into the content where relevant.
        - Mix: 40% Educational, 40% Entertaining, 20% Promotional.
        - Avoid generic advice; be specific to '{niche}'.
        """

        # Token budget scales with requested number of rows to avoid truncation.
        # Keeps routing deterministic (calendar uses reasoning model path).
        token_budget = min(2200, max(700, posts_per_month * 70))
        response = await self.llm_service.generate(
            prompt,
            task="calendar_generation",
            max_tokens=token_budget,
            user_id=user_id,
        )
        text = (response.get("text") or "").strip()

        if not self._is_valid_markdown_calendar(text, posts_per_month, content_formats):
            # One strict retry before failing fast.
            retry_prompt = f"""
            Return ONLY a markdown table.
            Columns exactly: | Post # | Date | Content Pillar | Topic | Format | Caption Hook |
            Use exactly {posts_per_month} rows.
            Month: {month} {year}. Niche: {niche}. Goal: {content_goals}.
            Allowed formats only: {format_str}.
            Festivals/events: {festival_str}.
            No intro text. No notes. No code fences.
            """
            retry_response = await self.llm_service.generate(
                retry_prompt,
                task="calendar_generation",
                max_tokens=max(token_budget, 1400),
                user_id=user_id,
            )
            text = (retry_response.get("text") or "").strip()

        if not self._is_valid_markdown_calendar(text, posts_per_month, content_formats):
            raise RuntimeError("Calendar generation failed: model returned invalid table format.")

        return text

    @staticmethod
    def _extract_table_rows(markdown: str) -> List[List[str]]:
        lines = [
            line.strip()
            for line in (markdown or "").splitlines()
            if line.strip().startswith("|") and line.strip().endswith("|")
        ]
        if len(lines) < 3:
            return []

        rows: List[List[str]] = []
        for i, line in enumerate(lines):
            if i == 1:
                # separator row
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if cells and any(cells):
                rows.append(cells)
        return rows

    @staticmethod
    def _normalize_format(value: str) -> str:
        return re.sub(r"[^a-z]", "", (value or "").strip().lower())

    def _is_valid_markdown_calendar(self, markdown: str, expected_rows: int, allowed_formats: List[str]) -> bool:
        rows = self._extract_table_rows(markdown)
        if not rows:
            return False
        if len(rows) < 2:
            return False

        header = [c.lower() for c in rows[0]]
        required_headers = ["post #", "date", "content pillar", "topic", "format", "caption hook"]
        if len(header) < len(required_headers):
            return False
        if any(required_headers[i] not in header[i] for i in range(len(required_headers))):
            return False

        data_rows = rows[1:]
        if len(data_rows) != expected_rows:
            return False

        allowed = {self._normalize_format(x) for x in allowed_formats}
        for row in data_rows:
            if len(row) < 6:
                return False
            fmt = self._normalize_format(row[4])
            if fmt not in allowed:
                return False
        return True

