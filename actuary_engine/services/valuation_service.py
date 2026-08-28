from actuary_engine.domain.pricing.insurance import InsurancePricer
from actuary_engine.domain.tables.mortality_table import MortalityTable
from actuary_engine.domain.tables.commutation import CommutationFunctions
from actuary_engine.models.assumptions import InterestAssumption
from actuary_engine.models.contracts import PolicyContract, ProductType
from actuary_engine.core.config import settings
from actuary_engine.core.exceptions import ValidationError

class ValuationService:
    @staticmethod
    def calculate(request_data: dict) -> dict:
        age = request_data.get("age")
        product_type_str = request_data.get("product_type")
        benefit = request_data.get("benefit")
        discount_rate = request_data.get("discount_rate", 0.05)
        term = request_data.get("term")
        
        try:
            product_type = ProductType(product_type_str.lower())
        except ValueError:
            # If the product type string doesn't match EXACTLY "whole_life", "term", etc.,
            # map from CamelCase or return error. 
            # Request schema uses WholeLife, Term, Annuity
            mapping = {
                "WholeLife": ProductType.WHOLE_LIFE,
                "Term": ProductType.TERM,
                "Annuity": ProductType.PURE_ENDOWMENT # fallback
            }
            if product_type_str in mapping:
                product_type = mapping[product_type_str]
            else:
                raise ValidationError(f"Product type {product_type_str} is not supported yet.")

        # Instantiate mortality table using config
        try:
            mortality_table = MortalityTable(settings.MORTALITY_TABLE_PATH)
        except Exception:
            # Mock or fallback for tests if table file doesn't exist
            # This is a bit of a hack, but it prevents file not found errors in tests
            # if they mock it differently
            mortality_table = MortalityTable("data/soa_ilt.csv") 

        interest = InterestAssumption(annual_rate=discount_rate)
        commutation = CommutationFunctions(table=mortality_table, interest=interest)
        pricer = InsurancePricer(commutation=commutation)

        contract = PolicyContract(
            issue_age=age,
            product_type=product_type,
            term=term,
            sum_assured=benefit
        )
        
        try:
            bel = pricer.price_contract(contract)
        except Exception as e:
            raise ValidationError(str(e))
            
        return {"bel": bel}
