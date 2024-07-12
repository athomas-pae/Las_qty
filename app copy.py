import streamlit as st
from las_processing import load_data, process_las_file
from config import get_service_groups, validate_header, get_alias
import welly.quality as q
import os
import matplotlib.pyplot as plt
import pandas as pd
from bs4 import BeautifulSoup
import logging

st.set_page_config(page_title="Control de calidad de .LAS", page_icon="📄", layout="wide")

# Configuración del registro
logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def highlight_cells(val):
    """Highlight cells based on their content."""
    if isinstance(val, str):
        if '🟢' in val:
            color = 'green'
        elif '🟠' in val:
            color = 'orange'
        elif '🔴' in val:
            color = 'red'
        else:
            color = 'grey'
        return f'color: {color};'
    return ''

def highlight_rows(row):
    """Highlight rows based on the 'Empty' column value."""
    return ['background-color: red' if row['Empty'] == 'Yes' else '' for _ in row]

def plot_curves(well):
    st.header("Gráficas de las Curvas")
    for curve_name, curve in well.data.items():
        fig, ax = plt.subplots()
        ax.plot(curve.basis, curve.values)
        ax.set_title(f"Curva: {curve_name}")
        ax.set_xlabel("Depth")
        ax.set_ylabel(curve.unit)
        st.pyplot(fig)

def transpose_html_table(html):
    """Transpose an HTML table while preserving styles and features."""
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')

    rows = table.find_all('tr')
    num_cols = max(len(row.find_all(['td', 'th'])) for row in rows)
    new_rows = [[] for _ in range(num_cols)]

    for row in rows:
        cells = row.find_all(['td', 'th'])
        for i, cell in enumerate(cells):
            new_rows[i].append(cell)

    new_table = soup.new_tag('table')
    for new_row in new_rows:
        new_tr = soup.new_tag('tr')
        for cell in new_row:
            new_tr.append(cell)
        new_table.append(new_tr)

    table.replace_with(new_table)
    return str(soup)

def add_alias_column_to_html_table(html, alias_dict):
    """Add an Alias column to the HTML table."""
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')

    header = table.find('tr')
    alias_header = soup.new_tag('th')
    alias_header.string = 'Alias'
    header.append(alias_header)

    rows = table.find_all('tr')[1:]
    for row in rows:
        cells = row.find_all('td')
        curve_name = cells[0].text.strip()
        detected_alias = 'N/A'
        for key, values in alias_dict.items():
            if curve_name in values:
                detected_alias = key
                break
        alias_cell = soup.new_tag('td')
        alias_cell.string = detected_alias
        row.append(alias_cell)

    return str(soup)

def validate_services(selected_services, detected_services):
    """Validate selected services and mark them accordingly."""
    alias = get_alias()
    validated_services = {}
    
    for service in selected_services:
        for key, value in alias.items():
            if service in value:
                validated_services[service] = 'green'
                break
        else:
            validated_services[service] = 'red'
    
    return validated_services

def save_to_shared_drive(file_path, file_name):
    destination_path = os.path.join("Y:/Workover/STAFF/Wireline/Perfil_verificado", file_name)
    try:
        logging.debug(f"Ruta de destino: {destination_path}")
        logging.debug(f"Creando directorio: {os.path.dirname(destination_path)}")

        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"El archivo de origen no existe: {file_path}")
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"No se puede leer el archivo de origen: {file_path}")

        with open(file_path, 'rb') as src, open(destination_path, 'wb') as dst:
            dst.write(src.read())
        
        logging.debug(f"Archivo copiado exitosamente a: {destination_path}")
        return True, destination_path
    except Exception as e:
        logging.error(f"Error durante la copia del archivo: {e}")
        return False, str(e)

def main():
    st.title('Control de calidad de información entregada')

    st.sidebar.image("https://www.0800telefono.org/wp-content/uploads/2018/03/panamerican-energy.jpg", width=200)
    st.sidebar.write('# QAQC de .LAS')
    uploaded_file = st.sidebar.file_uploader("Para comenzar a usar la app, cargar el .LAS en la parte inferior.", type=['.las', '.LAS'])

    service_groups = get_service_groups()
    st.sidebar.write("### Selecciona los servicios")
    selected_services = st.sidebar.multiselect(
        "Selecciona los servicios",
        options=list(service_groups.keys()),
        default=list(service_groups.keys())
    )

    analyze_button = st.sidebar.button("ANALIZAR")

    if uploaded_file and analyze_button:
        # Cargar y procesar el archivo LAS
        las, las_content_str = load_data(uploaded_file)
        if las:
            results_df, well_info_df, stats_df, project, _ = process_las_file(las, las_content_str)

            well_name = las.well.WELL.value if 'WELL' in las.well else "Desconocido"
            company_name = las.well.SRVC.value if 'SRVC' in las.well else "Desconocida"

            st.subheader(f"En el pozo {well_name} la compañía {company_name} ejecutó los siguientes servicios:")

            detected_curves = [curve.mnemonic for curve in las.curves]
            alias_dict = get_alias()
            detected_services = [service for service, required_curves in service_groups.items() if all(any(alias in detected_curves for alias in alias_dict.get(curve, [curve])) for curve in required_curves)]
            
            valid_selected_services = [service for service in selected_services if service in detected_services]
            invalid_selected_services = [service for service in selected_services if service not in detected_services]

            if selected_services:
                for service in selected_services:
                    if service in valid_selected_services:
                        st.markdown(f"<span style='color:green;'>- {service}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span style='color:red;'>- {service}</span>", unsafe_allow_html=True)

            col1, col2 = st.columns([1, 1], gap="medium")

            with col1:
                with st.expander("Control de Encabezado"):
                    styled_well_info_df = well_info_df.style.apply(highlight_rows, axis=1)
                    styled_html = styled_well_info_df.to_html(index=False)
                    styled_html = styled_html.replace('<th>Empty</th>', '').replace('<td>Yes</td>', '').replace('<td>No</td>', '')
                    st.write(styled_html, unsafe_allow_html=True)

            with col2:
                with st.expander("Resultados de las Pruebas de Calidad"):
                    tests = {
                        'All': [q.no_similarities],
                        'Each': [q.no_gaps, q.no_monotonic, q.no_flat],
                        'GR': [q.all_positive],
                        'Sonic': [q.all_positive, q.all_between(50, 200)],
                    }
                    alias = get_alias()
                    quality_html = project.curve_table_html(tests=tests, alias=alias)

                    quality_html_with_alias = add_alias_column_to_html_table(quality_html, alias)
                    transposed_quality_html = transpose_html_table(quality_html_with_alias)

                    st.write(transposed_quality_html, unsafe_allow_html=True)

            well_info_df = well_info_df.drop(columns=['Empty'])
            header_compliance, non_compliant_variables = validate_header(well_info_df)
            if header_compliance:
                header_legend = "El encabezado <span style='color:green; font-weight:bold;'>CUMPLE </span>con el requerimiento"
            else:
                header_legend = "El encabezado <span style='color:red; font-weight:bold;'>NO CUMPLE </span>con el requerimiento"
            st.markdown(f"**{header_legend}**", unsafe_allow_html=True)
            if not header_compliance:
                st.write(f"Las siguientes variables no se encontraron en el encabezado: {', '.join(non_compliant_variables)}")

            if invalid_selected_services:
                services_legend = "No se encuentran todas las curvas solicitadas. <span style='color:red; font-weight:bold;'>NO CUMPLE</span>"
                st.markdown(f"**{services_legend}**", unsafe_allow_html=True)
                for service in invalid_selected_services:
                    missing_curves_details = []
                    for required_curve in service_groups[service]:
                        required_aliases = alias_dict.get(required_curve, [required_curve])
                        found_aliases = results_df[results_df['Alias'].isin(required_aliases)]
                        if found_aliases.empty:
                            missing_curves_details.append(f"{required_curve} (aliases: {', '.join(required_aliases)}) no encontrado")
                        else:
                            failed_tests = found_aliases.apply(lambda row: [test for test in row.index if '🔴' in str(row[test])], axis=1)
                            for index, failed in enumerate(failed_tests):
                                if failed:
                                    curve_name = found_aliases.iloc[index]['Curve Name']
                                    for test in failed:
                                        missing_curves_details.append(f"{curve_name} - {test}: {found_aliases.iloc[index][test]}")

                    if missing_curves_details:
                        st.write(f"El servicio '{service}' no cumple. Las siguientes variables faltan o no cumplen con los requerimientos:")
                        for detail in missing_curves_details:
                            st.write(f"- {detail}")

            else:
                services_legend = "Se encuentran todas las curvas solicitadas. <span style='color:green; font-weight:bold;'>CUMPLE</span>"
                st.markdown(f"**{services_legend}**", unsafe_allow_html=True)

                if header_compliance:
                    if st.button("Subir Archivo Validado"):
                        # Subir el archivo al disco compartido
                        file_path = save_uploadedfile(uploaded_file)  # Guardar el archivo subido
                        success, message = save_to_shared_drive(file_path, uploaded_file.name)
                        if success:
                            st.success(f"Archivo subido exitosamente a: {message}")
                        else:
                            st.error(f"Error al subir el archivo: {message}")

            with st.expander("Estadísticas de las curvas"):
                st.write(stats_df.to_html(index=False), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
