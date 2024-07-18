"""Personality Schema."""

user_personality_mapping = {
    "Introversion/Extraversion": {
        "attribute": "introversion_extraversion",
        "label": "Introversion vs. Extraversion",
        "scale": ["Introverted", "Extraverted"],
        "description": "Measures preference for solitary activities versus social \
            interactions.",
    },
    "Thinking/Feeling": {
        "attribute": "thinking_feeling",
        "label": "Thinking vs. Feeling",
        "scale": ["Thinking", "Feeling"],
        "description": "Assesses reliance on logic versus emotions in decision making.",
    },
    "Sensing/Intuition": {
        "attribute": "sensing_intuition",
        "label": "Sensing vs. Intuition",
        "scale": ["Sensing", "Intuitive"],
        "description": "Indicates preference for concrete information versus abstract \
            ideas.",
    },
    "Judging/Perceiving": {
        "attribute": "judging_perceptive",
        "label": "Judging vs. Perceiving",
        "scale": ["Judging", "Perceiving"],
        "description": "Shows preference for structure versus flexibility in \
            lifestyle.",
    },
    "Conscientiousness": {
        "attribute": "conscientiousness",
        "label": "Conscientiousness",
        "scale": ["Careless", "Conscientious"],
        "description": "Reflects level of organization and dependability.",
    },
    "Agreeableness": {
        "attribute": "agreeableness",
        "label": "Agreeableness",
        "scale": ["Disagreeable", "Agreeable"],
        "description": "Indicates how cooperative and compassionate one is.",
    },
    "Neuroticism": {
        "attribute": "neuroticism",
        "label": "Neuroticism",
        "scale": ["Low", "High"],
        "description": "Measures emotional stability and tendency toward anxiety.",
    },
    "Individualism/Collectivism": {
        "attribute": "individualism_collectivism",
        "label": "Individualism vs. Collectivism",
        "scale": ["Individualistic", "Collectivistic"],
        "description": "Assesses preference for self-reliance versus group-oriented \
            behavior.",
    },
    "Libertarianism/Authoritarianism": {
        "attribute": "libertarianism_authoritarianism",
        "label": "Libertarianism vs. Authoritarianism",
        "scale": ["Libertarian", "Authoritarian"],
        "description": "Reflects preference for personal freedom versus structured \
            control.",
    },
    "Environmentalism/Anthropocentrism": {
        "attribute": "environmentalism_anthropocentrism",
        "label": "Environmentalism vs. Anthropocentrism",
        "scale": ["Environmental", "Anthropocentric"],
        "description": "Measures concern for the environment versus human-centered \
            interests.",
    },
    "Isolationism/Internationalism": {
        "attribute": "isolationism_interventionism",
        "label": "Isolationism vs. Internationalism",
        "scale": ["Isolationist", "Internationalist"],
        "description": "Indicates preference for national self-sufficiency versus \
            global cooperation.",
    },
    "Security/Freedom": {
        "attribute": "security_freedom",
        "label": "Security vs. Freedom",
        "scale": ["Security", "Freedom"],
        "description": "Measures preference for safety and stability versus autonomy.",
    },
    "Non-interventionism/Interventionism": {
        "attribute": "noninterventionism_interventionism",
        "label": "Interventionism",
        "scale": ["Low", "High"],
        "description": "Reflects preference for non-involvement versus active \
            involvement in others' affairs.",
    },
    "Equity/Meritocracy": {
        "attribute": "equity_meritocracy",
        "label": "Equity vs. Meritocracy",
        "scale": ["Equity", "Meritocracy"],
        "description": "Assesses preference for equality of outcome versus reward \
            based on ability.",
    },
    "Empathy": {
        "attribute": "empathy",
        "label": "Empathy",
        "scale": ["Low", "High"],
        "description": "Measures ability to understand and share the feelings of \
            others.",
    },
    "Honesty": {
        "attribute": "honesty",
        "label": "Honesty",
        "scale": ["Low", "High"],
        "description": "Reflects integrity and truthfulness in behavior.",
    },
    "Humility": {
        "attribute": "humility",
        "label": "Humility",
        "scale": ["Low", "High"],
        "description": "Indicates level of modesty and lack of arrogance.",
    },
    "Independence": {
        "attribute": "independence",
        "label": "Independence",
        "scale": ["Dependent", "Independent"],
        "description": "Measures self-reliance and autonomy in decision making.",
    },
    "Patience": {
        "attribute": "patience",
        "label": "Patience",
        "scale": ["Impatient", "Patient"],
        "description": "Reflects ability to wait calmly and tolerate delay.",
    },
    "Persistence": {
        "attribute": "persistence",
        "label": "Persistence",
        "scale": ["Low", "High"],
        "description": "Measures determination and perseverance in achieving goals.",
    },
    "Playfulness": {
        "attribute": "playfulness",
        "label": "Playfulness",
        "scale": ["Serious", "Playful"],
        "description": "Indicates tendency to engage in fun and light-hearted \
            activities.",
    },
    "Rationality": {
        "attribute": "rationality",
        "label": "Rationality",
        "scale": ["Irrational", "Rational"],
        "description": "Measures logical thinking and reason-based decision making.",
    },
    "Religiosity": {
        "attribute": "religiosity",
        "label": "Religiosity",
        "scale": ["Secular", "Religious"],
        "description": "Reflects level of religious belief and practice.",
    },
    "Self-acceptance": {
        "attribute": "self_acceptance",
        "label": "Self-Acceptance",
        "scale": ["Low", "High"],
        "description": "Measures satisfaction with oneself and acceptance of one's \
            flaws.",
    },
    "Sex Focus": {
        "attribute": "sex_focus",
        "label": "Sex Focus",
        "scale": ["Low", "High"],
        "description": "Indicates level of interest and priority given to sexual \
            matters.",
    },
    "Thriftiness": {
        "attribute": "thriftiness",
        "label": "Thriftiness",
        "scale": ["Generous", "Frugal"],
        "description": "Measures carefulness with money and avoidance of wasteful \
            spending.",
    },
    "Thrill-seeking": {
        "attribute": "thrill_seeking",
        "label": "Thrill-Seeking",
        "scale": ["Low", "High"],
        "description": "Indicates desire for excitement and adventurous activities.",
    },
    "Drug Friendliness": {
        "attribute": "drug_friendliness",
        "label": "Drug Friendliness",
        "scale": ["Low", "High"],
        "description": "Reflects openness versus adverseness of self or others using \
            drugs.",
    },
    "Emotional Openness in Relationships": {
        "negative": "Reserved",
        "positive": "Emotionally Open",
        "attribute": "emotional_openness_in_relationships",
        "label": "Emotional Openness",
        "scale": ["Low", "High"],
        "description": "Measures willingness to share emotions with a partner.",
    },
    "Equanimity": {
        "attribute": "equanimity",
        "label": "Equanimity",
        "scale": ["Low", "High"],
        "description": "Indicates emotional stability and calmness under stress.",
    },
    "Family Focus": {
        "attribute": "family_focus",
        "label": "Family Focus",
        "scale": ["Low", "High"],
        "description": "Reflects prioritization of family versus personal interests.",
    },
    "Loyalty": {
        "attribute": "loyalty",
        "label": "Loyalty",
        "scale": ["Low", "High"],
        "description": "Measures faithfulness and commitment to others.",
    },
    "Preference for Monogamy": {
        "attribute": "preference_for_monogamy",
        "label": "Preference for Monogamy",
        "scale": ["Low", "High"],
        "description": "Indicates preference for exclusive romantic relationships.",
    },
    "Trust": {
        "attribute": "trust",
        "label": "Trust",
        "scale": ["Distrustful", "Trusting"],
        "description": "Measures belief in the reliability and integrity of others.",
    },
    "Self-esteem": {
        "attribute": "self_esteem",
        "label": "Self-Esteem",
        "scale": ["Low", "High"],
        "description": "Reflects confidence and respect for oneself.",
    },
    "Anxious Attachment": {
        "attribute": "anxious_attachment",
        "label": "Anxious Attachment",
        "scale": ["Low", "High"],
        "description": "Measures tendency to experience anxiety in relationships.",
    },
    "Avoidant Attachment": {
        "attribute": "avoidant_attachment",
        "label": "Avoidant Attachment",
        "scale": ["Low", "High"],
        "description": "Indicates tendency to avoid intimacy and closeness in \
            relationships.",
    },
    "Career Focus": {
        "attribute": "career_focus",
        "label": "Career Focus",
        "scale": ["Low", "High"],
        "description": "Reflects the level of importance placed on one's career.",
    },
    "Emphasis on Boundaries": {
        "attribute": "emphasis_on_boundaries",
        "label": "Emphasis on Boundaries",
        "scale": ["Flexible", "Firm"],
        "description": "Measures the importance placed on setting and maintaining \
            personal boundaries.",
    },
    "Fitness Focus": {
        "attribute": "fitness_focus",
        "label": "Fitness Focus",
        "scale": ["Low", "High"],
        "description": "Reflects the level of importance placed on physical fitness.",
    },
    "Stability of Self-image": {
        "attribute": "stability_of_self_image",
        "label": "Stability of Self-Image",
        "scale": ["Low", "High"],
        "description": "Indicates consistency and stability in self-perception.",
    },
    "Love Focus": {
        "attribute": "love_focus",
        "label": "Love Focus",
        "scale": ["Low", "High"],
        "description": "Measures the importance placed on love and romantic \
            relationships.",
    },
    "Maturity": {
        "attribute": "maturity",
        "label": "Maturity",
        "scale": ["Low", "High"],
        "description": "Reflects the level of emotional and intellectual development.",
    },
    "Wholesomeness": {
        "attribute": "wholesomeness",
        "label": "Wholesomeness",
        "scale": ["Low", "High"],
        "description": "Measures the presence of virtuous and morally good qualities.",
    },
    "Traditionalism about Love": {
        "attribute": "traditionalist_view_of_love",
        "label": "Traditionalism about Love",
        "scale": ["Low", "High"],
        "description": "Reflects preference for conventional versus modern views on \
            love.",
    },
    "Openness to Experience": {
        "attribute": "openness_to_experience",
        "label": "Openness to Experience",
        "scale": ["Low", "High"],
        "description": "Measures willingness to try new things and embrace novel \
            experiences.",
    },
}
