import os
import json
import re
from typing import List, Dict
from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()

class QuizGenerator:
    def __init__(self):
        api_key = os.getenv("MISTRAL_API_KEY")
        self.client = None
        
        if api_key:
            try:
                self.client = Mistral(api_key=api_key)
                print("Mistral AI client initialized successfully")
            except Exception as e:
                print(f"Warning: Could not initialize Mistral client: {e}")
                self.client = None
    
    def extract_key_facts(self, article_text: str, title: str) -> List[Dict]:
        """Extract key facts from article to generate topic-specific questions"""
        facts = []
        
        # Extract dates/years
        dates = re.findall(r'\b(1[8-9]\d{2}|20\d{2})\b', article_text)
        if dates:
            facts.append({"type": "date", "values": list(set(dates[:5]))})
        
        # Extract key people (capitalized words that appear multiple times)
        words = re.findall(r'\b[A-Z][a-z]+\s[A-Z][a-z]+\b', article_text)
        people = [w for w in set(words) if w != title and len(w) > 5]
        if people:
            facts.append({"type": "people", "values": people[:5]})
        
        # Extract locations
        locations = re.findall(r'\b(?:University of\s\w+|\w+\sUniversity|\w+\sCollege|in\s[A-Z][a-z]+(?:,\s[A-Z][a-z]+)?)\b', article_text)
        if locations:
            facts.append({"type": "location", "values": list(set(locations[:5]))})
        
        # Extract numbers and statistics
        numbers = re.findall(r'\b\d+(?:\s*(?:million|billion|percent|years?|times?))?\b', article_text)
        if numbers:
            facts.append({"type": "number", "values": list(set(numbers[:5]))})
        
        return facts
    
    async def generate_quiz(self, article_text: str, title: str) -> List[Dict]:
        """Generate quiz from article text using Mistral AI (ASYNCHRONOUS)"""
        
        # Extract key facts first
        key_facts = self.extract_key_facts(article_text, title)
        
        # If no API client is available, return smart fallback quiz
        if self.client is None:
            print("No Mistral API configured. Using smart fallback quiz.")
            return self._create_smart_fallback_quiz(title, article_text, key_facts)
        
        # Speed Optimization: Use mistral-small-latest for significantly faster generation
        model_name = "mistral-small-latest"
        
        quiz_prompt = f"""You are an expert educational quiz creator. Based on the following Wikipedia article about "{title}", generate EXACTLY 5 high-quality quiz questions.

Article Content:
{article_text[:4000]}

Return ONLY a JSON array with EXACTLY 5 question objects.
Structure: [{{"question": "...", "options": ["...", "...", "...", "..."], "answer": "...", "difficulty": "...", "explanation": "..."}}]"""

        try:
            import random
            session_temperature = 0.7 + (random.random() * 0.2)
            
            # Using async completion for non-blocking execution
            response = await self.client.chat.complete_async(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are an expert quiz creator. Always respond with valid JSON containing exactly 5 questions."},
                    {"role": "user", "content": quiz_prompt}
                ],
                temperature=session_temperature,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            # Smart JSON parsing
            try:
                data = json.loads(content.strip())
                # Handle cases where model might wrap the list in a key
                if isinstance(data, dict):
                    if "questions" in data: quiz_data = data["questions"]
                    elif "quiz" in data: quiz_data = data["quiz"]
                    elif items := list(data.values()):
                        if isinstance(items[0], list): quiz_data = items[0]
                        else: quiz_data = [data]
                else:
                    quiz_data = data
            except:
                # Fallback extraction if JSON is messy
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                quiz_data = json.loads(json_match.group()) if json_match else []

            if not isinstance(quiz_data, list):
                quiz_data = [quiz_data]
            
            print(f"✅ Mistral ({model_name}) returned {len(quiz_data)} questions")
            return self._validate_quiz(quiz_data, title, article_text, key_facts)
            
        except Exception as e:
            print(f"❌ Error with Mistral API: {e}")
            return self._create_smart_fallback_quiz(title, article_text, key_facts)
    
    async def generate_related_topics(self, article_text: str, title: str) -> List[str]:
        """Generate related topics using Mistral AI (ASYNCHRONOUS)"""
        
        # If no API client is available, return smart topics
        if self.client is None:
            return self._extract_related_topics_from_content(title, article_text)
        
        # Performance: Use mistral-small-latest for faster topic generation
        model_name = "mistral-small-latest"
        
        topics_prompt = f"""Based on the Wikipedia article about "{title}", identify 6-8 specific related Wikipedia topics for further reading.

Article Content:
{article_text[:3000]}

Return only a comma-separated list of 6-8 Wikipedia article titles."""

        try:
            response = await self.client.chat.complete_async(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": topics_prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            # Parse topics
            topics_text = response.choices[0].message.content.strip()
            # Clean up potential LLM conversational prefix
            if ":" in topics_text and len(topics_text.split(":")[0]) < 30:
                topics_text = topics_text.split(":", 1)[1].strip()
                
            topics = [t.strip().strip('"\'') for t in topics_text.split(',') if t.strip() and len(t.strip()) > 2]
            
            print(f"✅ Mistral ({model_name}) generated {len(topics)} related topics")
            return topics[:8] if topics else self._extract_related_topics_from_content(title, article_text)
            
        except Exception as e:
            print(f"Error generating related topics: {e}")
            return self._extract_related_topics_from_content(title, article_text)
    
    def _extract_related_topics_from_content(self, title: str, article_text: str) -> List[str]:
        """Extract related topics from article content"""
        topics = []
        
        # Common related topic patterns
        common_topics = {
            "science": ["Scientific method", "History of science", "Physics", "Chemistry", "Biology"],
            "technology": ["Computer science", "Engineering", "Innovation", "Artificial intelligence"],
            "history": ["World history", "Ancient history", "Modern history", "Historiography"],
            "people": ["Biography", "Notable people", "Historical figures"],
            "war": ["Military history", "Diplomacy", "Peace studies"],
            "art": ["Art history", "Visual arts", "Cultural movements"],
            "math": ["Mathematics", "Geometry", "Calculus"]
        }
        
        # Check for keywords in article
        text_lower = article_text.lower()
        for category, related in common_topics.items():
            if category in text_lower:
                topics.extend(related)
        
        # Add some generic but relevant topics
        if not topics:
            topics = ["Related concepts", "Historical context", "Further reading", "See also"]
        
        return list(set(topics))[:8]
    
    def _validate_quiz(self, quiz_data: List[Dict], title: str, article_text: str, key_facts: List[Dict]) -> List[Dict]:
        """Validate and clean quiz data - MUST return exactly 5 questions"""
        validated = []
        
        for item in quiz_data:
            if all(key in item for key in ['question', 'options', 'answer', 'difficulty', 'explanation']):
                # Ensure options is a list
                if isinstance(item['options'], str):
                    item['options'] = [opt.strip() for opt in item['options'].split(',')]
                
                # Ensure we have exactly 4 options
                if len(item['options']) == 4:
                    # Validate difficulty
                    difficulty = item['difficulty'].lower()
                    if difficulty not in ['easy', 'medium', 'hard']:
                        difficulty = 'medium'
                    item['difficulty'] = difficulty
                    
                    # Ensure answer is in options
                    if item['answer'] not in item['options']:
                        for opt in item['options']:
                            if item['answer'].lower() in opt.lower() or opt.lower() in item['answer'].lower():
                                item['answer'] = opt
                                break
                    
                    validated.append(item)
        
        # Ensure we have exactly 5 questions
        if len(validated) < 5:
            fallback = self._create_smart_fallback_quiz(title, article_text, key_facts)
            validated.extend(fallback)
        
        return validated[:5]
    
    def _create_smart_fallback_quiz(self, title: str, article_text: str, key_facts: List[Dict]) -> List[Dict]:
        """Create exactly 5 smart fallback questions"""
        questions = []
        
        # Extract facts
        dates = []
        people = []
        locations = []
        for fact in key_facts:
            if fact['type'] == 'date':
                dates = fact['values']
            elif fact['type'] == 'people':
                people = fact['values']
            elif fact['type'] == 'location':
                locations = fact['values']
        
        # Question 1: About the main subject - EASY
        questions.append({
            "question": f"What is '{title}' primarily known for?",
            "options": [
                "A significant contribution to its field",
                "A historical event or discovery",
                "A major scientific breakthrough",
                "An important cultural development"
            ],
            "answer": "A significant contribution to its field",
            "difficulty": "easy",
            "explanation": f"{title} is recognized as an important subject with notable contributions."
        })
        
        # Question 2: Time period - MEDIUM
        if dates:
            questions.append({
                "question": f"In which time period is {title} primarily associated?",
                "options": [f"Early {dates[0]}s", f"Mid {dates[0]}s", f"Late {dates[0]}s", "Ancient times"],
                "answer": f"Mid {dates[0]}s",
                "difficulty": "medium",
                "explanation": f"{title} is associated with the period around {dates[0]}."
            })
        else:
            questions.append({
                "question": f"When did {title} first emerge or become significant?",
                "options": ["In the early 20th century", "In the mid 20th century", "In the late 20th century", "In the 21st century"],
                "answer": "In the late 20th century",
                "difficulty": "medium",
                "explanation": f"{title} emerged during a significant period of development."
            })
        
        # Question 3: Key figures - MEDIUM
        if people and len(people) > 0:
            questions.append({
                "question": f"Which notable figure is associated with {title}?",
                "options": [
                    people[0] if len(people) > 0 else "A prominent leader",
                    people[1] if len(people) > 1 else "A key collaborator",
                    people[2] if len(people) > 2 else "A contemporary figure",
                    "An anonymous contributor"
                ],
                "answer": people[0] if len(people) > 0 else "A prominent leader",
                "difficulty": "medium",
                "explanation": f"{people[0] if len(people) > 0 else 'Notable figures'} played an important role."
            })
        else:
            questions.append({
                "question": f"What is a key characteristic of {title}?",
                "options": ["It is highly innovative", "It is widely used", "It is technologically advanced", "All of the above"],
                "answer": "All of the above",
                "difficulty": "medium",
                "explanation": f"{title} has multiple important characteristics."
            })
        
        # Question 4: Location - MEDIUM
        if locations and len(locations) > 0:
            questions.append({
                "question": f"Where is {title} primarily associated with?",
                "options": [
                    locations[0] if len(locations) > 0 else "A major institution",
                    locations[1] if len(locations) > 1 else "A significant location",
                    "Multiple locations worldwide",
                    "An unknown location"
                ],
                "answer": locations[0] if len(locations) > 0 else "A major institution",
                "difficulty": "medium",
                "explanation": f"{title} has strong associations with {locations[0] if len(locations) > 0 else 'important locations'}."
            })
        else:
            questions.append({
                "question": f"In what context is {title} most commonly used?",
                "options": ["In educational settings", "In professional environments", "In everyday life", "All of the above"],
                "answer": "All of the above",
                "difficulty": "medium",
                "explanation": f"{title} is applicable in various contexts."
            })
        
        # Question 5: Significance - HARD
        questions.append({
            "question": f"What is the broader significance of {title}?",
            "options": [
                "It influenced subsequent developments",
                "It marked a turning point in history",
                "It established new standards",
                "All of the above"
            ],
            "answer": "All of the above",
            "difficulty": "hard",
            "explanation": f"{title} has wide-ranging influence and significance."
        })
        
        return questions[:5]