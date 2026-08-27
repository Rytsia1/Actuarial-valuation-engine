"""
Insurance product contract data models.

Provides Pydantic v2 data structures for life insurance policy contracts,
product types, and benefit specifications. Contracts are pure data — they
carry no calculation logic and are consumed by pricing/valuation engines.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ProductType(str, Enum):
    """Enumeration of supported life insurance product types.

    Each type determines the benefit structure and applicable pricing formula:
    - TERM: Death benefit only, fixed duration.
    - WHOLE_LIFE: Death benefit, lifetime coverage.
    - ENDOWMENT: Death benefit + survival benefit at maturity.
    - PURE_ENDOWMENT: Survival benefit only at maturity.
    """

    TERM = "term"
    WHOLE_LIFE = "whole_life"
    ENDOWMENT = "endowment"
    PURE_ENDOWMENT = "pure_endowment"


class PolicyContract(BaseModel):
    """Single life insurance policy contract specification.

    Represents the contractual terms of a life insurance policy, including
    the product type, coverage duration, face amount, and premium payment
    structure. Used as input to pricing and valuation engines.

    Attributes:
        product_type: Type of insurance product.
        issue_age: Age at issue (x).
        term: Coverage duration in years (None for whole life).
        sum_assured: Face amount / death benefit.
        premium_paying_term: Premium payment period (None = same as term).
        policy_id: Optional unique policy identifier.
    """

    product_type: ProductType = Field(
        ...,
        description="Type of life insurance product.",
    )
    issue_age: int = Field(
        ...,
        ge=0,
        description="Age at policy issue (x).",
    )
    term: Optional[int] = Field(
        default=None,
        gt=0,
        description="Coverage duration in years. None for whole life.",
    )
    sum_assured: float = Field(
        default=1_000_000.0,
        gt=0.0,
        description="Face amount / sum assured.",
    )
    premium_paying_term: Optional[int] = Field(
        default=None,
        gt=0,
        description="Premium payment period in years. None = same as coverage term.",
    )
    policy_id: Optional[str] = Field(
        default=None,
        description="Optional unique policy identifier.",
    )

    @model_validator(mode="after")
    def validate_contract(self) -> "PolicyContract":
        """Validate structural contract consistency.

        Structural Rules:
        - Whole life products must not have a finite term.
        - Non-whole-life products must have a positive term.
        - Premium paying term must not exceed coverage term if finite term is specified.
        Note: Exact maximum age limits (omega) are governed by the MortalityTable
        used for pricing/valuation via `validate_against_table(table)`.
        """
        if self.product_type == ProductType.WHOLE_LIFE:
            if self.term is not None:
                raise ValueError(
                    "Whole life products should not have a finite term. "
                    "Set term=None for whole life coverage."
                )
        else:
            if self.term is None:
                raise ValueError(
                    f"{self.product_type.value} products require a finite term."
                )

        if self.term is not None and self.premium_paying_term is not None:
            if self.premium_paying_term > self.term:
                raise ValueError(
                    f"Premium paying term ({self.premium_paying_term}) cannot exceed "
                    f"coverage term ({self.term})."
                )

        return self

    def validate_against_table(self, table: Any) -> None:
        """Validate that contract parameters conform to the mortality table's boundaries.

        The mortality table is the source of truth for maximum age (omega) and minimum age:
        - Issue age must be within [table.min_age, table.max_age].
        - For finite-term products, issue_age + term must not exceed table.max_age.
        - Premium paying term (if specified) must not exceed remaining years to table.max_age.

        Args:
            table: MortalityTable instance (or object with min_age, max_age, name).

        Raises:
            ValueError: If issue age or term exceeds the mortality table limits.
        """
        min_age = int(table.min_age)
        max_age = int(table.max_age)
        table_name = getattr(table, "name", "MortalityTable")

        if self.issue_age < min_age:
            raise ValueError(
                f"Issue age ({self.issue_age}) is below the mortality table minimum age "
                f"of {min_age} ({table_name})."
            )
        if self.issue_age > max_age:
            raise ValueError(
                f"Issue age ({self.issue_age}) exceeds the mortality table maximum age "
                f"(omega) of {max_age} ({table_name})."
            )

        max_available_term = max_age - self.issue_age

        if self.product_type != ProductType.WHOLE_LIFE:
            if self.term is not None and self.issue_age + self.term > max_age:
                raise ValueError(
                    f"Issue age ({self.issue_age}) + term ({self.term}) = "
                    f"{self.issue_age + self.term} exceeds mortality table maximum age "
                    f"(omega) of {max_age} ({table_name}). Maximum allowable term for "
                    f"issue age {self.issue_age} is {max_available_term} years."
                )

        if self.premium_paying_term is not None:
            effective_coverage = self.term if self.term is not None else max_available_term
            if self.premium_paying_term > effective_coverage:
                raise ValueError(
                    f"Premium paying term ({self.premium_paying_term}) exceeds "
                    f"maximum allowable duration ({effective_coverage}) under mortality table "
                    f"{table_name} (omega={max_age})."
                )

    @property
    def effective_premium_term(self) -> Optional[int]:
        """Effective premium payment duration.

        Returns the premium paying term if explicitly set, otherwise the
        coverage term. Returns None for whole life with no premium paying
        term specified (premiums paid for life).
        """
        if self.premium_paying_term is not None:
            return self.premium_paying_term
        return self.term

    @property
    def is_limited_pay(self) -> bool:
        """Whether this is a limited-pay policy (premium term < coverage term)."""
        if self.premium_paying_term is None:
            return False
        if self.term is None:
            # Whole life with limited pay
            return True
        return self.premium_paying_term < self.term
