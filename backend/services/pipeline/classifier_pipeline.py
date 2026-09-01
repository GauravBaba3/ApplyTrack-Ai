"""
Master Classification Pipeline Orchestrator for ApplyTrack AI.

Executes the strictly gated tiered AI escalation pipeline:
1. Triage Priority Evaluation (P1, P2, P3)
2. Tier 1: Deterministic Rule Engine (RuleEngine pattern families, negative context, domain heuristics)
   - If rule confidence is high (>= 0.85 or is_deterministic_final) AND entities identified: Final Decision (HF & LLM SKIPPED)
3. Tier 2: Hugging Face zero-shot classifier (if rule confidence is low / uncertain)
   - If Hugging Face confidence is high (>= 0.85): Final Decision (LLM SKIPPED)
4. Tier 3: LLM Fallback Chain (if Hugging Face remains uncertain)
   - Groq -> Google Gemini -> OpenRouter
5. Tier 4: Human Review (if all automated stages remain uncertain or confidence < 0.70)
"""
import logging
from typing import Dict, Any

from .rule_engine import RuleEngine, RuleCategory
from .triage_service import TriageService
from .hf_service import HFService
from .llm_fallback_service import LLMFallbackService

logger = logging.getLogger(__name__)


class ClassifierPipeline:
    """
    Tiered classification pipeline combining deterministic rules, HF zero-shot models, and LLM fallbacks.
    Enforces strict early exits when higher tiers achieve high confidence.
    """

    RULE_HIGH_CONFIDENCE_THRESHOLD = 0.85
    HF_HIGH_CONFIDENCE_THRESHOLD = 0.85
    REVIEW_THRESHOLD = 0.70

    @classmethod
    def process_email(cls, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute full classification pipeline for an email message.

        Returns:
            Dict containing is_job_related, confidence, triage_priority,
            company, job_title, status, event_type, interview_date, needs_review,
            rule_evidence_score, hf_score, llm_confidence, and tier_used.
        """
        # Step 0: Initial Triage Priority Queue (P1 / P2 / P3)
        triage_priority, triage_reason = TriageService.determine_priority(email_data)

        # Step 1: Tier 1 - Deterministic Rule Engine Evaluation
        rule_eval = RuleEngine.evaluate(email_data)

        is_rule_job = rule_eval['is_job_related']
        rule_confidence = rule_eval['confidence']
        rule_evidence_score = rule_eval['evidence_score']
        extracted_company = rule_eval['company']
        extracted_title = rule_eval['job_title']
        rule_status = rule_eval['status']
        rule_event = rule_eval['event_type']
        is_deterministic_final = rule_eval['is_deterministic_final']

        result = {
            'is_job_related': is_rule_job,
            'confidence': rule_confidence,
            'rule_evidence_score': rule_confidence,
            'rule_points': rule_evidence_score,
            'rule_category': rule_eval['category'],
            'hf_score': None,
            'llm_confidence': None,
            'triage_priority': triage_priority,
            'triage_reason': triage_reason,
            'company': extracted_company or '',
            'job_title': extracted_title or '',
            'status': rule_status or 'Applied',
            'event_type': rule_event or 'other',
            'interview_date': None,
            'needs_review': False,
            'tier_used': 'rule_engine'
        }

        # Early exit for definite non-job items (e.g. newsletters, digests, low rule score)
        if rule_evidence_score < 20 and not is_rule_job and triage_priority == 'P3':
            result['is_job_related'] = False
            result['confidence'] = 0.05
            result['needs_review'] = False
            return result

        # Rule Engine High Confidence Check:
        # If the rule engine is confident and has identified key details or matches strong pattern family
        if is_deterministic_final or (is_rule_job and rule_confidence >= cls.RULE_HIGH_CONFIDENCE_THRESHOLD and result['company']):
            logger.debug(f"Rule Engine deterministic decision (score={rule_evidence_score}, conf={rule_confidence:.2f}) for message. HF & LLM skipped.")
            result['needs_review'] = False
            return result

        # Step 2: Tier 2 - Hugging Face Zero-Shot Classifier (only called when rule engine is uncertain)
        subject_and_snippet = f"{email_data.get('subject', '')} {email_data.get('snippet', '')}"
        hf_result = HFService.classify_email_zero_shot(subject_and_snippet)

        if hf_result:
            top_label = hf_result.get('top_label', '')
            hf_score = float(hf_result.get('score', 0.0))
            result['hf_score'] = hf_score

            if top_label == 'not job related' and hf_score >= cls.HF_HIGH_CONFIDENCE_THRESHOLD:
                result['is_job_related'] = False
                result['confidence'] = 0.05
                result['tier_used'] = 'huggingface'
                result['needs_review'] = False
                return result
            hf_map = {
                'job interview invitation': ('Interview', 'interview_invitation', 'P1'),
                'job offer letter': ('Offer', 'offer', 'P1'),
                'job application rejection': ('Rejected', 'rejection', 'P1'),
                'technical coding assessment': ('Assessment', 'coding_assessment', 'P2'),
                'job application received confirmation': ('Applied', 'application_received', 'P2'),
            }

            if top_label in hf_map:
                st, ev, prio = hf_map[top_label]
                result['triage_priority'] = prio
                if hf_score >= cls.HF_HIGH_CONFIDENCE_THRESHOLD:
                    result['is_job_related'] = True
                    result['status'] = st
                    result['event_type'] = ev
                    result['confidence'] = hf_score
                    result['tier_used'] = 'huggingface'
                    result['needs_review'] = False
                    if result['company']:
                        return result

        # Step 3: Tier 3 - LLM Provider Fallback (Groq -> Gemini -> OpenRouter)
        # Called when Rule Engine and HF remain uncertain or missing structured entities
        llm_res = LLMFallbackService.classify_email(email_data)
        if llm_res and llm_res.get('is_job_related') is not None:
            llm_is_job = llm_res.get('is_job_related', False)
            llm_conf = float(llm_res.get('confidence', 0.5))

            result['is_job_related'] = llm_is_job
            result['llm_confidence'] = llm_conf
            result['confidence'] = max(rule_confidence, llm_conf)
            result['company'] = llm_res.get('company') or result['company']
            result['job_title'] = llm_res.get('job_title') or result['job_title']
            result['status'] = llm_res.get('status') or result['status']
            result['event_type'] = llm_res.get('event_type') or result['event_type']
            result['interview_date'] = llm_res.get('interview_date')
            result['tier_used'] = f"llm_{llm_res.get('provider', 'fallback')}"

            # Re-evaluate triage priority based on structured LLM result
            if result['event_type'] in ['interview_invitation', 'interview_scheduling', 'offer', 'rejection', 'position_filled', 'candidate_not_selected']:
                result['triage_priority'] = 'P1'
            elif result['event_type'] in ['coding_assessment', 'assessment_invitation', 'application_received', 'application_confirmation', 'application_status_update']:
                result['triage_priority'] = 'P2'

        # Step 4: Tier 4 - Human Review Determination & Status Safety
        # Protect against premature destructive status updates (Rejected, Offer, Withdrawn)
        if result['is_job_related']:
            if result['status'] in ['Rejected', 'Offer', 'Withdrawn'] and result['confidence'] < 0.85 and not is_deterministic_final:
                result['needs_review'] = True
                result['review_reason'] = f"Conservative protection: {result['status']} status requires >= 0.85 confidence (got {result['confidence']:.2f})"
            elif result['confidence'] < cls.REVIEW_THRESHOLD or not result['company']:
                result['needs_review'] = True
                result['review_reason'] = "Low confidence (< 0.70) or missing company entity"
        elif not is_deterministic_final:
            # Uncertain email where AI providers were exhausted or failed
            result['needs_review'] = True
            result['review_reason'] = "AI providers unavailable or exhausted for uncertain email"

        return result
