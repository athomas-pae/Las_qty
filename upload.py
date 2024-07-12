import logging
import os
import streamlit as st

# Configuración del registro
logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

st.set_page_config(page_title="Control de calidad de .LAS", page_icon="📄", layout="wide")

def save_uploadedfile(uploadedfile, temp_dir="tempDir"):
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, uploadedfile.name)
    with open(file_path, "wb") as f:
        f.write(uploadedfile.getbuffer())
    return file_path

def save_to_shared_drive(file_path, file_name):
    destination_path = os.path.join("Y:/Workover/STAFF/Wireline/Perfil_verificado", file_name)
    try:
        logging.debug(f"Creando directorio: {os.path.dirname(destination_path)}")
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        with open(file_path, 'rb') as src, open(destination_path, 'wb') as dst:
            dst.write(src.read())
        
        logging.debug(f"Archivo copiado exitosamente a: {destination_path}")
        return True, destination_path
    except Exception as e:
        logging.error(f"Error durante la copia del archivo: {e}")
        return False, str(e)

def main():
    st.title('Control de calidad de información entregada')
    uploaded_file = st.file_uploader("Cargar archivo .LAS", type=['.las', '.LAS'])
    
    if uploaded_file is not None:
        st.write(f"Detalles del archivo subido: Nombre - {uploaded_file.name}, Tipo - {uploaded_file.type}")

        # Guardar archivo subido en directorio temporal
        temp_file_path = save_uploadedfile(uploaded_file)
        st.success(f"Archivo guardado temporalmente en: {temp_file_path}")
        logging.debug(f"Archivo guardado temporalmente en: {temp_file_path}")

        # Verificar que el archivo temporal existe y tiene contenido
        if os.path.exists(temp_file_path) and os.path.getsize(temp_file_path) > 0:
            st.write("El archivo temporal está listo para subir.")
            logging.debug(f"Archivo temporal '{temp_file_path}' verificado y está listo para subir")

            # Intentar subir el archivo al disco compartido
            if st.button("Subir archivo al disco compartido"):
                logging.debug("Botón de subir archivo presionado")
                success, message = save_to_shared_drive(temp_file_path, uploaded_file.name)
                if success:
                    st.success(f"Archivo subido exitosamente a: {message}")
                    logging.debug(f"Archivo subido exitosamente a: {message}")
                else:
                    st.error(f"Error al subir el archivo: {message}")
                    logging.error(f"Error al subir el archivo: {message}")
        else:
            st.error("Error: el archivo temporal no existe o está vacío.")
            logging.error(f"Error: el archivo temporal '{temp_file_path}' no existe o está vacío.")

if __name__ == "__main__":
    main()
