import streamlit as st
from las_processing import load_data, process_las_file
from config import get_service_groups, validate_header, get_alias
import os

st.set_page_config(page_title="Control de calidad de .LAS", page_icon="📄", layout="wide")

# CSS para achicar las letras de los checkboxes
st.sidebar.markdown(
    """
    <style>
    .sidebar .checkbox-label {
        font-size: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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

def main():
    st.title('Control de calidad de información entregada')

    # Sidebar Options & File Upload
    st.sidebar.image("https://www.0800telefono.org/wp-content/uploads/2018/03/panamerican-energy.jpg", width=200)
    st.sidebar.write('# QAQC de .LAS')
    uploaded_file = st.sidebar.file_uploader("Para comenzar a usar la app, cargar el .LAS en la parte inferior.", type=['.las', '.LAS'])

    # Importar y mostrar opciones para seleccionar servicios en la barra lateral
    service_groups = get_service_groups()
    st.sidebar.write("### Selecciona los servicios")
    selected_services = st.sidebar.multiselect(
        "Selecciona los servicios",
        options=list(service_groups.keys()),
        default=list(service_groups.keys())
    )

    # Agregar botón ANALIZAR en la barra lateral
    analyze_button = st.sidebar.button("ANALIZAR")

    # Procesar solo si se ha cargado un archivo y se ha presionado el botón ANALIZAR
    if uploaded_file and analyze_button:
        las, las_content_str = load_data(uploaded_file)
        if las:
            results_df, well_info_df, stats_df = process_las_file(las, las_content_str)

            well_name = las.well.WELL.value if 'WELL' in las.well else "Desconocido"
            company_name = las.well.SRVC.value if 'SRVC' in las.well else "Desconocida"

            st.subheader(f"En el pozo {well_name} la compañía {company_name} ejecutó los siguientes servicios:")

            # Detectar los servicios basados en el archivo .LAS
            detected_services = [service for service, required_curves in service_groups.items() if all(any(alias in results_df['Alias'].values for alias in get_alias().get(curve, [curve])) for curve in required_curves)]

            # Filtrar los servicios seleccionados por el usuario que están presentes en los servicios detectados
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
                    # Aplicamos el estilo a las filas según el valor de 'Empty'
                    styled_well_info_df = well_info_df.style.apply(highlight_rows, axis=1)
                    # Convertimos a HTML
                    styled_html = styled_well_info_df.to_html(index=False)
                    # Eliminamos las referencias a la columna 'Empty' del HTML resultante
                    styled_html = styled_html.replace('<th>Empty</th>', '').replace('<td>Yes</td>', '').replace('<td>No</td>', '')
                    st.write(styled_html, unsafe_allow_html=True)

            with col2:
                with st.expander("Resultados de las Pruebas de Calidad"):
                    styled_df = results_df.style.applymap(highlight_cells)
                    st.write(styled_df.to_html(escape=False), unsafe_allow_html=True)

            # Eliminamos la columna 'Empty' después de aplicar los estilos
            well_info_df = well_info_df.drop(columns=['Empty'])
            header_compliance, non_compliant_variables = validate_header(well_info_df)
            if header_compliance:
                header_legend = "El encabezado <span style='color:green; font-weight:bold;'>CUMPLE </span>con el requerimiento"
            else:
                header_legend = "El encabezado <span style='color:red; font-weight:bold;'>NO CUMPLE </span>con el requerimiento"
            st.markdown(f"**{header_legend}**", unsafe_allow_html=True)
            if not header_compliance:
                st.write(f"Las siguientes variables no se encontraron en el encabezado: {', '.join(non_compliant_variables)}")

            # Mostrar leyenda de cumplimiento de servicios y detallar las curvas que no cumplen
            alias = get_alias()
            if invalid_selected_services:
                services_legend = "No se encuentran todas las curvas solicitadas. <span style='color:red; font-weight:bold;'>NO CUMPLE</span>"
                st.markdown(f"**{services_legend}**", unsafe_allow_html=True)
                for service in invalid_selected_services:
                    missing_curves_details = []
                    for required_curve in service_groups[service]:
                        required_aliases = alias.get(required_curve, [required_curve])
                        found_aliases = results_df[results_df['Alias'].isin(required_aliases)]
                        if found_aliases.empty:
                            missing_curves_details.append(f"{required_curve} (aliases: {', '.join(required_aliases)}) no encontrado")
                        else:
                            # Detallar por qué no cumplen las pruebas
                            failed_tests = found_aliases.apply(lambda row: [test for test in row.index if '🔴' in str(row[test])], axis=1)
                            for index, failed in enumerate(failed_tests):
                                if failed:
                                    curve_name = found_aliases.iloc[index]['Curve']
                                    for test in failed:
                                        missing_curves_details.append(f"{curve_name} - {test}: {found_aliases.iloc[index][test]}")

                    if missing_curves_details:
                        st.write(f"El servicio '{service}' no cumple. Las siguientes variables faltan o no cumplen con los requerimientos:")
                        for detail in missing_curves_details:
                            st.write(f"- {detail}")

            else:
                services_legend = "Se encuentran todas las curvas solicitadas. <span style='color:green; font-weight:bold;'>CUMPLE</span>"
                st.markdown(f"**{services_legend}**", unsafe_allow_html=True)

            # Mostrar tabla de estadísticas de las curvas
            st.subheader("Estadísticas de las curvas")
            st.write(stats_df)

if __name__ == "__main__":
    main()

