from typing import Dict, Any
from fastapi import HTTPException
import json

class ScoreKeeper:

    weights: dict

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ScoreKeeper, cls).__new__(cls)
            cls.instance._load_weights()
        return cls.instance


    def _load_weights(self) -> Dict | None:
        try:
            with open('./scores.json', 'r') as f:
                self.weights = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def _calculate_trait_scores(self, user_answers: Dict[str, bool], questions_scores: Dict[str, Any]) -> Dict[str, float]:
        traits_scores = {trait: {'cumulative_score': 0.0, 'count': 0} for question in questions_scores.values() for trait in question.keys()}
        
        for question, answer in user_answers.items():
            if question in questions_scores:
                for trait, scores in questions_scores[question].items():
                    presence_score = scores['presence_given_yes'] if answer else scores['presence_given_no']
                    traits_scores[trait]['cumulative_score'] += presence_score
                    traits_scores[trait]['count'] += 1
        
        normalized_scores = {}
        for trait, data in traits_scores.items():
            if data['count'] > 0:
                raw_score = data['cumulative_score'] / data['count']
                weight = 4
                if raw_score > 0.5:
                    weighted_score = 0.5 + (raw_score - 0.5) * weight
                else:
                    weighted_score = 0.5 - (0.5 - raw_score) * weight
                normalized_score = min(max(weighted_score, 0.0), 1.0)
            else:
                normalized_score = 0.0
            normalized_scores[trait] = normalized_score

        return normalized_scores

    def calculate_individual(self, user_answers: Dict[str, bool], questions_scores: Dict[str, Any]) -> Dict[str, float]:
        return self._calculate_trait_scores(user_answers, questions_scores)

