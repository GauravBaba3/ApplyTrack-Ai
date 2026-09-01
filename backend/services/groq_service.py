"""
Groq API service for AI classification.
"""
import logging
import json
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class GroqService:
    """Service for interacting with Groq API."""
    
    API_URL = 'https://api.groq.com/openai/v1/chat/completions'
    
    @classmethod
    def classify_email(cls, email_data, user=None):
        """
        Classify an email as job-related and extract structured information.
        
        Args:
            email_data: Dictionary containing email information
            user: Optional user for logging
            
        Returns:
            Dictionary with classification results
        """
        try:
            # Prepare prompt
            prompt = cls._build_classification_prompt(email_data)
            
            # Call Groq API
            response = cls._call_groq(prompt)
            
            # Parse and validate response
            result = cls._parse_response(response)
            
            return result
            
        except Exception as e:
            logger.error(f"Groq classification failed: {str(e)}")
            return {
                'is_job_related': False,
                'confidence': 0.0,
                'error': str(e)
            }
    
    @classmethod
    def generate_followup_draft(cls, application):
        """
        Generate a follow-up email draft for an application.
        
        Args:
            application: Application model instance
            
        Returns:
            Dictionary with subject and body
        """
        try:
            prompt = cls._build_followup_prompt(application)
            response = cls._call_groq(prompt)
            
            # Parse response
            result = cls._parse_followup_response(response)
            
            return result
            
        except Exception as e:
            logger.error(f"Groq follow-up generation failed: {str(e)}")
            return {
                'subject': 'Follow-up on my application',
                'body': 'Dear Hiring Team,\n\nI hope this email finds you well. I wanted to follow up on my application for the [Job Title] position at [Company].\n\nThank you for your time and consideration.\n\nBest regards,'
            }
    
    @classmethod
    def _build_classification_prompt(cls, email_data):
        """Build the prompt for email classification."""
        sender = email_data.get('sender', '')
        subject = email_data.get('subject', '')
        snippet = email_data.get('snippet', '')
        body = email_data.get('body', '')
        
        # Truncate long content
        snippet = snippet[:1000] if snippet else ''
        body = body[:2000] if body else ''
        
        prompt = f"""You are an expert job application tracker. Classify this email and extract structured information.

Email Details:
- From: {sender}
- Subject: {subject}
- Snippet: {snippet}
- Body: {body}

Task: Determine if this email is related to a job application. If it is, extract the company name, job title, event type, status, and any relevant dates.

Return ONLY a valid JSON object with this structure:
{{
    "is_job_related": true/false,
    "company": "Company Name" or null,
    "job_title": "Job Title" or null,
    "status": "Applied" or "Assessment" or "Interview" or "Offer" or "Rejected" or "Withdrawn" or "Pending" or "No Response" or "Ghosted" or "Unknown" or null,
    "event_type": "application_confirmation" or "application_received" or "interview_invitation" or "assessment_invitation" or "recruiter_outreach" or "rejection" or "offer" or "next_round" or "hiring_manager_message" or "coding_assessment" or "interview_scheduling" or "application_status_update" or "position_filled" or "candidate_not_selected" or "application_withdrawn" or "other" or null,
    "interview_date": "YYYY-MM-DDTHH:MM:SS" or null,
    "confidence": 0.0 to 1.0
}}

Important:
- Only return valid JSON, no other text
- If not job-related, set is_job_related to false
- Be conservative: if unsure, set is_job_related to false
- Extract dates in ISO 8601 format if mentioned
- Confidence should reflect your certainty"""
        
        return prompt
    
    @classmethod
    def _build_followup_prompt(cls, application):
        """Build the prompt for follow-up draft generation."""
        company = application.company
        job_title = application.job_title
        days_since_activity = (timezone.now() - application.last_activity_date).days if application.last_activity_date else 14
        
        prompt = f"""You are a professional job applicant. Create a concise, polite follow-up email.

Application Details:
- Company: {company}
- Job Title: {job_title}
- Days since last activity: {days_since_activity}

Task: Write a professional follow-up email that:
1. Is polite and professional
2. References the specific job application
3. Asks for an update on the application status
4. Is brief (3-4 sentences maximum)

Return ONLY a valid JSON object with this structure:
{{
    "subject": "Email subject line",
    "body": "Email body text"
}}

Important:
- Only return valid JSON, no other text
- Keep the email professional and to the point"""
        
        return prompt
    
    @classmethod
    def _call_groq(cls, prompt):
        """Call Groq API with the given prompt."""
        api_key = settings.GROQ_API_KEY
        
        if not api_key:
            raise Exception("GROQ_API_KEY not configured")
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        primary_model = getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
        models = [primary_model, 'llama-3.1-8b-instant', 'llama-3.3-70b-versatile']
        last_error = None

        for model_name in models:
            payload = {
                'model': model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.2,
                'max_tokens': 1000,
                'response_format': {
                    'type': 'json_object'
                }
            }
            
            try:
                response = requests.post(
                    cls.API_URL,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    import time
                    time.sleep(1.5)
                    retry_res = requests.post(
                        cls.API_URL,
                        headers=headers,
                        json=payload,
                        timeout=30
                    )
                    if retry_res.status_code == 200:
                        return retry_res.json()
                    last_error = retry_res.text
                else:
                    logger.warning(f"Groq model {model_name} returned {response.status_code}: {response.text}")
                    last_error = response.text
            except requests.exceptions.RequestException as e:
                logger.error(f"Groq API request with {model_name} failed: {str(e)}")
                last_error = str(e)
                
        raise Exception(f"All Groq models failed. Last error: {last_error}")
    
    @classmethod
    def _parse_response(cls, response_data):
        """Parse and validate Groq response for classification."""
        try:
            # Get the content from the response
            content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if not content:
                return {
                    'is_job_related': False,
                    'confidence': 0.0,
                    'error': 'No content in response'
                }
            
            # Parse JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from the content
                # Sometimes the model wraps JSON in markdown code blocks
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    return {
                        'is_job_related': False,
                        'confidence': 0.0,
                        'error': 'Invalid JSON in response'
                    }
            
            # Validate required fields
            if 'is_job_related' not in result:
                result['is_job_related'] = False
            
            if 'confidence' not in result:
                result['confidence'] = 0.5
            
            # Clamp confidence between 0 and 1
            result['confidence'] = max(0.0, min(1.0, float(result.get('confidence', 0.5))))
            
            # Clean up null values
            for key in ['company', 'job_title', 'status', 'event_type', 'interview_date']:
                if key in result and result[key] is None:
                    del result[key]
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse Groq response: {str(e)}")
            return {
                'is_job_related': False,
                'confidence': 0.0,
                'error': str(e)
            }
    
    @classmethod
    def _parse_followup_response(cls, response_data):
        """Parse and validate Groq response for follow-up draft."""
        try:
            content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if not content:
                return {
                    'subject': 'Follow-up on my application',
                    'body': 'Dear Hiring Team,\n\nI hope this email finds you well. I wanted to follow up on my application.\n\nThank you for your time.\n\nBest regards,'
                }
            
            # Parse JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    return {
                        'subject': 'Follow-up on my application',
                        'body': content
                    }
            
            # Validate fields
            subject = result.get('subject', 'Follow-up on my application')
            body = result.get('body', 'Dear Hiring Team,\n\nI hope this email finds you well. I wanted to follow up on my application.\n\nThank you for your time.\n\nBest regards,')
            
            return {
                'subject': subject,
                'body': body
            }
            
        except Exception as e:
            logger.error(f"Failed to parse follow-up response: {str(e)}")
            return {
                'subject': 'Follow-up on my application',
                'body': 'Dear Hiring Team,\n\nI hope this email finds you well. I wanted to follow up on my application.\n\nThank you for your time.\n\nBest regards,'
            }
