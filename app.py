import os
import streamlit as st
import shutil
from las_processing import load_data, process_las_file
from config import get_service_groups, get_alias, validate_header
import welly.quality as q
import pandas as pd
from bs4 import BeautifulSoup

def save_uploadedfile(uploadedfile, temp_dir="tempDir"):
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, uploadedfile.name)
    
    # Implementación de la barra de progreso
    with open(file_path, "wb") as f:
        file_size = uploadedfile.size
        chunk_size = 1024 * 1024  # 1 MB
        bytes_read = 0

        progress = st.progress(0)
        
        while bytes_read < file_size:
            chunk = uploadedfile.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            bytes_read += len(chunk)
            progress.progress(min(bytes_read / file_size, 1.0))
        
        progress.empty()

    return file_path

def save_to_shared_drive(file_path, file_name, fld_value, well_name):
    destination_folder = os.path.join("Y:/Workover/STAFF/Wireline/Perfil_verificado", fld_value, well_name)
    destination_path = os.path.join(destination_folder, file_name)
    try:
        os.makedirs(destination_folder, exist_ok=True)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"El archivo de origen no existe: {file_path}")
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"No se puede leer el archivo de origen: {file_path}")

        with open(file_path, 'rb') as src:
            total_size = os.path.getsize(file_path)
            copied_size = 0
            chunk_size = 1024 * 1024  # 1 MB
            progress = st.progress(0)
            
            with open(destination_path, 'wb') as dst:
                while True:
                    chunk = src.read(chunk_size)
                    if not chunk:
                        break
                    dst.write(chunk)
                    copied_size += len(chunk)
                    progress.progress(min(copied_size / total_size, 1.0))
        
        progress.empty()
        return True, destination_path
    except FileNotFoundError as fnf_error:
        return False, str(fnf_error)
    except PermissionError as perm_error:
        return False, str(perm_error)
    except Exception as e:
        return False, str(e)

def highlight_rows(row):
    return ['background-color: red' if row['Empty'] == 'Yes' else '' for _ in row]

def highlight_cells(val):
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

def transpose_html_table(html):
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

def main():
    st.title('Control de calidad de información entregada')

    st.sidebar.image("https://www.0800telefono.org/wp-content/uploads/2018/03/panamerican-energy.jpg", width=200)
    st.sidebar.write('# QAQC de .LAS')
    
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None
    if 'temp_file_path' not in st.session_state:
        st.session_state.temp_file_path = None
    if 'analysis_done' not in st.session_state:
        st.session_state.analysis_done = False

    uploaded_file = st.sidebar.file_uploader("Para comenzar a usar la app, cargar el .LAS en la parte inferior.", type=['.las', '.LAS'])

    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        st.session_state.temp_file_path = save_uploadedfile(uploaded_file)
        st.session_state.analysis_done = False

    service_groups = get_service_groups()
    st.sidebar.write("### Selecciona los servicios")
    selected_services = st.sidebar.multiselect(
        "Selecciona los servicios",
        options=list(service_groups.keys()),
        default=list(service_groups.keys())
    )

    analyze_button = st.sidebar.button("ANALIZAR")

    if analyze_button and st.session_state.uploaded_file:
        las, las_content_str = load_data(open(st.session_state.temp_file_path, 'rb'))
        if las:
            results_df, well_info_df, stats_df, project, _ = process_las_file(las, las_content_str)

            well_name = las.well.WELL.value if 'WELL' in las.well else "Desconocido"
            company_name = las.well.SRVC.value if 'SRVC' in las.well else "Desconocida"
            date = las.well.DATE.value if 'DATE' in las.well else "SinFecha"
            fld_value = las.well.FLD.value if 'FLD' in las.well else "SinCampo"

            st.subheader(f"En el pozo {well_name} la compañía {company_name} ejecutó los siguientes servicios:")

            detected_curves = [curve.mnemonic for curve in las.curves]
            alias_dict = get_alias()
            detected_services = [service for service, required_curves in service_groups.items() if all(any(alias in detected_curves for alias in alias_dict.get(curve, [curve])) for curve in required_curves)]
            
            detected_services_str = "-".join(detected_services) if detected_services else "NoServices"

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
            header_complies = header_compliance  # Variable para determinar si el encabezado cumple

            if header_compliance:
                header_legend = "El encabezado <span style='color:green; font-weight:bold;'>CUMPLE </span>con el requerimiento"
            else:
                header_legend = "El encabezado <span style='color:red; font-weight:bold;'>NO CUMPLE </span>con el requerimiento"
            st.markdown(f"**{header_legend}**", unsafe_allow_html=True)
            if not header_compliance:
                st.write(f"Las siguientes variables no se encontraron en el encabezado: {', '.join(non_compliant_variables)}")

            services_complies = False  # Variable para determinar si los servicios cumplen
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
                services_complies = True

            st.session_state.analysis_done = True

            with st.expander("Estadísticas de las curvas"):
                st.write(stats_df.to_html(index=False), unsafe_allow_html=True)

            # Intentar copiar el archivo si ambas condiciones se cumplen
            if header_complies and services_complies:
                st.write("El encabezado y los servicios cumplen con los requerimientos. Subiendo el archivo...")
                
                new_file_name = f"{well_name}_{date}_{detected_services_str}-{company_name}.las"
                new_file_name = new_file_name.replace(" ", "_")  # Reemplazar espacios por guiones bajos
                
                success, message = save_to_shared_drive(st.session_state.temp_file_path, new_file_name, fld_value, well_name)
                if success:
                    st.success(f"Archivo subido exitosamente a: {message}")
                else:
                    st.error(f"Error al subir el archivo: {message}")

if __name__ == "__main__":
    main()
