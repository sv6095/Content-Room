import holidays
from datetime import datetime
from typing import List, Dict, Any
from services.llm_service import LLMService

class CalendarService:
    def __init__(self):
        self.llm_service = LLMService()
        self.indian_holidays = holidays.India()

    async def generate_calendar(
        self,
        month: str,
        year: int,
        niche: str,
        content_goals: str,
        content_formats: List[str],
        posts_per_month: int,
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
        
        response = await self.llm_service.generate(prompt, task="calendar_generation")
        return response.get("text", "Failed to generate calendar")

