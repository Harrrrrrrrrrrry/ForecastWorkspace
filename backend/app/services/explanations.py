from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.models.schemas import ExplanationResponse, ForecastResponse


ALLOWED_FORECAST_SIGNALS = {"bullish", "bearish", "neutral", "uncertain"}


class ForecastExplanationService:
    """Generate explanation text from structured model outputs only."""

    def __init__(self, client: OpenAI | None = None) -> None:
        self.settings = get_settings()
        self.client = client or self._build_client()

    def explain(self, forecast: ForecastResponse) -> ExplanationResponse:
        if not self.client:
            raise RuntimeError("OpenAI API key is not configured.")

        # Academic rule: the explanation layer receives only structured backend output.
        # The LLM is never asked to infer prices, change the forecast, or perform the model logic.
        response = self.client.responses.create(
            model=self.settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": self._system_prompt(),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": self._user_prompt(forecast),
                        }
                    ],
                },
            ],
        )

        raw_text = self._extract_output_text(response)
        parsed = self._parse_json_response(raw_text)

        return ExplanationResponse(
            model=self.settings.openai_model,
            plain_language_explanation=parsed["plain_language_explanation"],
            reliability_summary=parsed["reliability_summary"],
            limitations_summary=parsed["limitations_summary"],
            forecast_signal=parsed["forecast_signal"],
            disclaimer=parsed["disclaimer"],
        )

    def _build_client(self) -> OpenAI | None:
        if not self.settings.openai_api_key:
            return None
        return OpenAI(api_key=self.settings.openai_api_key)

    def _system_prompt(self) -> str:
        return (
            "You are the explanation layer for an academic stock forecasting platform. "
            "You must explain only the structured forecast data you are given. "
            "Do not generate, revise, or optimize predictions. "
            "Do not provide financial advice. "
            "Return valid JSON with exactly these keys: "
            "plain_language_explanation, reliability_summary, limitations_summary, "
            "forecast_signal, disclaimer. "
            "forecast_signal must be exactly one of: bullish, bearish, neutral, uncertain."
        )

    def _user_prompt(self, forecast: ForecastResponse) -> str:
        structured_payload = json.dumps(forecast.model_dump(mode="json"), indent=2, sort_keys=True)
        return (
            "Using only the structured forecast payload below, produce a concise explanation for a user. "
            "The explanation must summarize what the forecast predicts, how reliable it appears, the most "
            "important limitations, a forecast_signal classification, and a clear non-financial-advice disclaimer. "
            "If the payload includes multiple model curves or ensemble components, explain how they were blended "
            "and whether any supplemental model was unavailable. "
            "If the payload contains warnings or fallback behavior, mention them explicitly. "
            "Choose forecast_signal only from the payload's predicted direction, warnings, fallback behavior, "
            "confidence or reliability indicators, and missing supplemental model availability. "
            "Use bullish for an upward prediction with no major warning and acceptable reliability. "
            "Use bearish for a downward prediction with no major warning and acceptable reliability. "
            "Use neutral for a very small or mixed predicted change. "
            "Use uncertain when warnings, fallback behavior, missing supplemental models, or weak reliability "
            "materially reduce confidence. "
            "Do not output buy, sell, or hold advice. Keep all text concise and professional. "
            "Do not invent facts beyond the payload. Do not generate a new prediction.\n\n"
            f"{structured_payload}"
        )

    def _extract_output_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text

        output = getattr(response, "output", None)
        if not output:
            raise ValueError("OpenAI response did not contain any output text.")

        text_parts: list[str] = []
        for item in output:
            content = getattr(item, "content", None) or item.get("content", [])
            for part in content:
                part_type = getattr(part, "type", None) or part.get("type")
                if part_type in {"output_text", "text"}:
                    text_value = getattr(part, "text", None) or part.get("text")
                    if text_value:
                        text_parts.append(text_value)

        if not text_parts:
            raise ValueError("OpenAI response did not contain any parsable text output.")

        return "\n".join(text_parts)

    def _parse_json_response(self, raw_text: str) -> dict[str, str]:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json\n", "", 1).strip()

        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("Explanation response must be a JSON object.")

        required_keys = {
            "plain_language_explanation",
            "reliability_summary",
            "limitations_summary",
            "forecast_signal",
            "disclaimer",
        }
        missing_keys = required_keys.difference(parsed.keys())
        if missing_keys:
            missing_list = ", ".join(sorted(missing_keys))
            raise ValueError(f"Explanation response is missing required keys: {missing_list}")

        extra_keys = set(parsed.keys()).difference(required_keys)
        if extra_keys:
            extra_list = ", ".join(sorted(extra_keys))
            raise ValueError(f"Explanation response contains unexpected keys: {extra_list}")

        cleaned_payload = {key: str(parsed[key]).strip() for key in required_keys}
        forecast_signal = cleaned_payload["forecast_signal"].lower()
        if forecast_signal not in ALLOWED_FORECAST_SIGNALS:
            allowed = ", ".join(sorted(ALLOWED_FORECAST_SIGNALS))
            raise ValueError(
                f"Explanation response has invalid forecast_signal '{cleaned_payload['forecast_signal']}'. "
                f"Expected one of: {allowed}"
            )

        cleaned_payload["forecast_signal"] = forecast_signal
        return cleaned_payload
