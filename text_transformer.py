import os
import openai
from config import OPENAI_API_KEY, CELEBRITIES


class TextTransformer:
    def __init__(self):
        """Initialize the OpenAI client with API key"""
        openai.api_key = OPENAI_API_KEY
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)

    def transform_text(self, text, celebrity_id):
        """Transform text to mimic a celebrity's speaking style"""
        # Get celebrity info
        if celebrity_id not in CELEBRITIES:
            raise ValueError(f"Celebrity {celebrity_id} not found")

        celebrity = CELEBRITIES[celebrity_id]

        # Create prompt for OpenAI
        prompt = self._create_prompt(text, celebrity)

        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system",
                        "content": f"You are {celebrity['name']}. Respond in first person with the speaking style, vocabulary, and mannerisms that {celebrity['name']} would use. IMPORTANT: Always respond in the SAME LANGUAGE as the user's input - if they write in Portuguese, Spanish, or any other language, you must respond in that SAME language."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error calling OpenAI API: {str(e)}")
            return text  # Return original text if API call fails

    def _create_prompt(self, text, celebrity):
        """Create a prompt for the OpenAI API"""
        name = celebrity["name"]
        description = celebrity["description"]

        if name == "Cristiano Ronaldo":
            return f"""
            I want you to respond as if you are Cristiano Ronaldo. Rewrite the following text in the way Cristiano 
            would express it, with his confidence, passion for football, and occasional references to his achievements.
            Include some of his Portuguese-influenced English phrases if appropriate. Sometimes add his 
            famous "Siuuu" celebration or mention your determination and work ethic.
            
            IMPORTANT: You MUST respond in the SAME LANGUAGE as the original text. If the text is in Portuguese,
            respond in Portuguese. If it's in English, respond in English, etc.
            
            Here's the text: "{text}"
            
            Respond as Cristiano Ronaldo:
            """
        elif name == "Donald Trump":
            return f"""
            I want you to respond as if you are Donald Trump. Rewrite the following text in Trump's distinctive 
            speaking style, with his repetitive patterns, use of superlatives ("tremendous", "the best", "huge"), 
            and simple, direct language. Include some of his characteristic phrases like "believe me", 
            "many people are saying", etc. where appropriate.
            
            IMPORTANT: You MUST respond in the SAME LANGUAGE as the original text. If the text is in Portuguese,
            respond in Portuguese. If it's in English, respond in English, etc.
            
            Here's the text: "{text}"
            
            Respond as Donald Trump:
            """
        else:
            return f"""
            I want you to respond as if you are {name}. {description}
            
            IMPORTANT: You MUST respond in the SAME LANGUAGE as the original text. If the text is in Portuguese,
            respond in Portuguese. If it's in English, respond in English, etc.
            
            Here's the text: "{text}"
            
            Respond as {name}:
            """
