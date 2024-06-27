from pydantic import BaseModel
from typing import Dict

# Refined trait names
trait_names = {
    "Introversion/Extraversion": ["Introverted", "Extraverted"],
    "Thinking/Feeling": ["Thinking", "Feeling"],
    "Sensing/Intuition": ["Sensing", "Intuitive"],
    "Judging/Perceiving": ["Judging", "Perceiving"],
    "Conscientiousness": ["Careless", "Conscientious"],
    "Agreeableness": ["Disagreeable", "Agreeable"],
    "Neuroticism": ["Non-Neurotic", "Neurotic"],
    "Individualism/Collectivism": ["Individualistic", "Collectivistic"],
    "Libertarianism/Authoritarianism": ["Libertarian", "Authoritarian"],
    "Environmentalism/Anthropocentrism": ["Environmental", "Anthropocentric"],
    "Isolationism/Internationalism": ["Isolationist", "Internationalist"],
    "Security/Freedom": ["Security-focused", "Freedom-focused"],
    "Non-interventionism/Interventionism": ["Non-Interventionist", "Interventionist"],
    "Equity/Meritocracy": ["Equity-focused", "Meritocracy-focused"],
    "Empathy": ["Indifferent", "Empathetic"],
    "Honesty": ["Dishonest", "Honest"],
    "Humility": ["Proud", "Humble"],
    "Independence": ["Dependent", "Independent"],
    "Patience": ["Impatient", "Patient"],
    "Persistence": ["Inconsistent", "Persistent"],
    "Playfulness": ["Serious", "Playful"],
    "Rationality": ["Irrational", "Rational"],
    "Religiosity": ["Secular", "Religious"],
    "Self-acceptance": ["Self-Critical", "Self-Accepting"],
    "Sex Focus": ["Non-Sex-Focused", "Sex-Focused"],
    "Thriftiness": ["Generous", "Frugal"],
    "Thrill-seeking": ["Cautious", "Thrill-seeking"],
    "Drug Friendliness": ["Drug-averse", "Drug-friendly"],
    "Emotional Openness in Relationships": ["Reserved", "Emotionally Open"],
    "Equanimity": ["Reactive", "Equanimous"],
    "Family Focus": ["Individual-focused", "Family-focused"],
    "Loyalty": ["Disloyal", "Loyal"],
    "Preference for Monogamy": ["Non-Monogamous", "Monogamous"],
    "Trust": ["Distrustful", "Trusting"],
    "Self-esteem": ["Low Self-esteem", "High Self-esteem"],
    "Anxious Attachment": ["Not Anxious", "Anxious"],
    "Avoidant Attachment": ["Not Avoidant", "Avoidant"],
    "Career Focus": ["Not Career-focused", "Career-focused"],
    "Emphasis on Boundaries": ["Flexible Boundaries", "Firm Boundaries"],
    "Fitness Focus": ["Not Fitness-focused", "Fitness-focused"],
    "Stability of Self-image": ["Unstable Self-Image", "Stable Self-Image"],
    "Love Focus": ["Love-averse", "Love-focused"],
    "Maturity": ["Immature", "Mature"],
    "Wholesomeness": ["Unwholesome", "Wholesome"],
    "Traditionalism about Love": ["Non-Traditional", "Traditional"],
    "Openness to Experience": ["Closed to Experience", "Open to Experience"]
}


class UserAnswers(BaseModel):
    answers: Dict[str, bool]

