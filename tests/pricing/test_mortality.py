import pytest
import pandas as pd
import numpy as np

def test_survival_probability(mortality_table):
    # Manually compute tPx for age=30, t=5 using the soa_ilt.csv table loaded as a pandas.DataFrame.
    # We simulate loading the dataframe as instructed
    df = pd.read_csv("soa_ilt.csv")
    
    # We assume 'age' and 'l_x' columns exist in soa_ilt.csv
    l_30 = df.loc[df['age'] == 30, 'l_x'].values[0]
    l_35 = df.loc[df['age'] == 35, 'l_x'].values[0]
    expected_tpx = l_35 / l_30
    
    engine_tpx = mortality_table.survival_prob(age=30, t=5)
    assert np.isclose(engine_tpx, expected_tpx, rtol=1e-12)

def test_survival_at_max_age(mortality_table):
    max_age = mortality_table.get_max_age()
    assert mortality_table.survival_prob(age=max_age, t=1) == 0.0
