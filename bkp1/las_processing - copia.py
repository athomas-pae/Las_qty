import lasio
from welly import Project
import welly.quality as qty
import welly
import io
import os
import pandas as pd
from config import get_alias, get_tests, has_si_units

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
            
            content_io = io.StringIO(content_str)
            las = lasio.read(content_io)
            return las, content_str
        except Exception as e:
            st.error(f"Error al cargar el archivo LAS: {e}")
            return None, None

    return None, None

def process_las_file(las, las_content_str):
    """Process the LAS file to extract information and perform quality checks."""
    try:
        with open("temp.las", "w") as temp_file:
            temp_file.write(las_content_str)
        
        p = Project.from_las("temp.las")
        os.remove("temp.las")
    except Exception as e:
        st.error(f"Error processing LAS file: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    alias = get_alias()
    tests = get_tests()
    tests['Each'].append(lambda curve: has_si_units(curve))

    table_data = []
    stats_data = []
    for well in p:
        for curve_name, curve in well.data.items():
            curve_alias = [k for k, v in alias.items() if curve_name in v]
            curve_alias = curve_alias[0] if curve_alias else 'N/A'
            curve_tests = tests.get(curve_alias, tests['Each'])
            test_results = apply_tests(curve, curve_tests, curve_name)

            row = {
                'Curve': curve_name,
                'Alias': curve_alias,
                'Mean Value': curve.mean(),
                'Units': curve.units if curve.units else "N/A"
            }
            row.update(test_results)
            table_data.append(row)

            stats_data.append({
                'Curve': curve_name,
                'Alias': curve_alias,
                'Min Value': curve.min(),
                'Max Value': curve.max(),
                'Mean Value': curve.mean(),
                'Units': curve.units if curve.units else "N/A"
            })

    results_df = pd.DataFrame(table_data)
    results_df['Mean Value'] = results_df['Mean Value'].apply(lambda x: f"{x:.2f}" if x is not None else "N/A")

    stats_df = pd.DataFrame(stats_data)
    stats_df['Min Value'] = stats_df['Min Value'].apply(lambda x: f"{x:.2f}" if x is not None else "N/A")
    stats_df['Max Value'] = stats_df['Max Value'].apply(lambda x: f"{x:.2f}" if x is not None else "N/A")
    stats_df['Mean Value'] = stats_df['Mean Value'].apply(lambda x: f"{x:.2f}" if x is not None else "N/A")
    
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
