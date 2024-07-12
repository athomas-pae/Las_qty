import lasio
from welly import Well
import welly.quality as qty
import io
import os
import pandas as pd
from config import get_alias, get_tests, has_si_units
import streamlit as st

def load_data(uploaded_file):
    """Load and decode the LAS file."""
    if uploaded_file is not None:
        try:
            content_bytes = uploaded_file.read()
            for encoding in ['utf-8', 'latin1', 'windows-1252']:
                try:
                    content_str = content_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise UnicodeDecodeError("Unable to decode file with common encodings.")
            
            las = lasio.read(io.StringIO(content_str))
            return las, content_str
        except Exception as e:
            st.error(f"Error al cargar el archivo LAS: {e}")
            return None, None

    return None, None

def process_las_file(las, las_content_str):
    """Process the LAS file to extract information and perform quality checks."""
    try:
        # Crear un archivo temporal desde el contenido LAS
        with open("temp.las", "w") as temp_file:
            temp_file.write(las_content_str)
        
        # Leer el archivo LAS usando Welly
        well = Well.from_las("temp.las")
        os.remove("temp.las")
    except Exception as e:
        st.error(f"Error processing LAS file: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    alias = get_alias()
    tests = get_tests()
    tests['Each'].append(lambda curve: has_si_units(curve))

    table_data = []
    stats_data = []
    for curve_name, curve in well.data.items():
        curve_alias = [k for k, v in alias.items() if curve_name in v]
        curve_alias = curve_alias[0] if curve_alias else 'N/A'
        curve_tests = tests.get(curve_alias, tests['Each'])
        test_results = apply_tests(curve, curve_tests, curve_name)

        # Convert the curve data to a DataFrame
        curve_df = pd.DataFrame(curve.values, columns=[curve_name])
        curve_stats = curve_df.describe()
        mean_value = curve_stats.loc['mean'][curve_name] if 'mean' in curve_stats.index else None
        min_value = curve_stats.loc['min'][curve_name] if 'min' in curve_stats.index else None
        max_value = curve_stats.loc['max'][curve_name] if 'max' in curve_stats.index else None

        row = {
            'Curve Name': curve_name,
            'Alias': curve_alias,
            'Mean Value': mean_value if pd.notna(mean_value) else None,
            'Test Results': ''.join(test_results.values())
        }
        table_data.append(row)

        stats_data.append({
            'Curve Name': curve_name,
            'Min Value': min_value if pd.notna(min_value) else None,
            'Max Value': max_value if pd.notna(max_value) else None,
            'Mean Value': mean_value if pd.notna(mean_value) else None
        })

    results_df = pd.DataFrame(table_data)
    results_df['Mean Value'] = results_df['Mean Value'].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else "N/A")

    stats_df = pd.DataFrame(stats_data)
    stats_df['Min Value'] = stats_df['Min Value'].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else "N/A")
    stats_df['Max Value'] = stats_df['Max Value'].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else "N/A")
    stats_df['Mean Value'] = stats_df['Mean Value'].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else "N/A")
    
    well_info_data = {"MNEM": [], "Value": [], "Description": [], "Empty": []}
    for item in las.well:
        well_info_data["MNEM"].append(item.mnemonic)
        well_info_data["Value"].append(item.value)
        well_info_data["Description"].append(item.descr)
        well_info_data["Empty"].append('Yes' if item.value == '' or item.value is None else 'No')
    well_info_df = pd.DataFrame(well_info_data)
    well_info_df = well_info_df.sort_values(by='Empty', ascending=False)

    return results_df, well_info_df, stats_df

def apply_tests(curve, tests, curve_name):
    """Apply quality tests to a curve and return the results."""
    results = {}
    for test in tests:
        test_name = test.__name__.replace('_', ' ').capitalize()
        try:
            result = test(curve)
            if result is True:
                results[test_name] = f'<span style="color:green;" title="{curve_name} - {test_name}: All tests passed">🟢</span>'
            elif result is False:
                results[test_name] = f'<span style="color:orange;" title="{curve_name} - {test_name}: Some tests failed">🟠</span>'
            else:
                results[test_name] = f'<span style="color:red;" title="{curve_name} - {test_name}: All tests failed">🔴</span>'
        except Exception:
            results[test_name] = f'<span style="color:grey;" title="{curve_name} - {test_name}: No tests ran">⚪</span>'
    return results
