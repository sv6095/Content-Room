import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException
from services.llm_service import LLMService
from utils.optimization import TokenOptimizer

class CompetitorService:
    def __init__(self):
        self.llm_service = LLMService()

    async def scrape_profile(self, url: str) -> str:
        """
        Scrapes textual content from a social profile URL.
        Note: Actual scraping of major platforms (Insta, Twitter, LinkedIn) is blocked by robots/CAPTCHAs.
        This provides a basic implementation for public web pages or allowed sites.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Basic headers to mimic browser
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    # Fallback: Just return URL as context if scraping fails
                    return f"Profile URL: {url} (Content not accessible, analyzing based on URL structure)"

                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract meta description and main content text
                meta_desc = soup.find("meta", {"name": "description"})
                description = meta_desc["content"] if meta_desc else ""
                
                # Get visible text (simple extraction)
                texts = soup.stripped_strings
                content_sample = " ".join([t for t in texts if len(t) > 20])[:2000] # Limit to 2000 chars

                return f"Profile Description: {description}\nSample Content: {content_sample}"
                
        except Exception as e:
            # If scraping fails completely, return the URL as context
            return f"Profile URL: {url} (Scraping error: {str(e)})"



    async def analyze_competitor_gaps(self, competitor_url: str, my_niche: str) -> str:
        """
        Analyzes a competitor's content strategy and identifies gaps.
        """
        scraped_data = await self.scrape_profile(competitor_url)
        
        # Optimization: Compress the scraped content to save tokens
        optimized_data = TokenOptimizer.compress_context(scraped_data, aggressive=True)
        
        prompt = f"""
        Analyze the following competitor content data and identify content gaps for my niche: '{my_niche}'.
        
        Competitor Data:
        {optimized_data}
        
        Task:
        1. Identify their main content themes.
        2. Identify what they are MISSING or doing poorly.
        3. Suggest 3 specific content ideas that would outperform them in the '{my_niche}' niche.
        
        Output format:
        ## Competitor Strategy
        - Theme 1...
        
        ## Gaps & Opportunities
        - Gap 1...
        
        ## Winning Content Ideas
        1. [Idea 1]
        2. [Idea 2]
        3. [Idea 3]
        """
        
        # Use LLM to generate analysis
        # Using a default provider, assuming setup is correct
        response = await self.llm_service.generate(prompt, task="competitor_analysis")
        return response.get("text", "Analysis failed")
