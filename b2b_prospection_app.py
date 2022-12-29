import sys
sys.path.append("code")
sys.path.append("data")

import streamlit as st
from streamlit_authenticator import Authenticate, Hasher
from st_switcher import st_switcher
import yaml
from app import *
from about import *
from utils import *

if 'b2b_report_env' not in st.session_state:
    st.session_state['b2b_report_env'] = b2b_report()
if 'sidebar_state' not in st.session_state:
    st.session_state['sidebar_state'] = 'collapsed'

st.set_page_config(page_title="B2B prospection",
                    layout="centered",
                    page_icon=":handshake:",
                    initial_sidebar_state=st.session_state.sidebar_state)

# Autentificação ----------------------------------------------------------------------------------------- 
with open('data/config.yaml') as file:
    config = yaml.load(file, Loader=yaml.SafeLoader)

authenticator = Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
if 'authentication_username' not in st.session_state:
    st.session_state['authentication_username'] = None

with st.sidebar:
    name, st.session_state['authentication_status'], st.session_state['authentication_username'] = authenticator.login('Login', 'main')

    if st.session_state.authentication_status:
        authenticator.logout('Logout', 'main')
        st.success(f'Welcome *{name}*')
    elif st.session_state.authentication_status == False:
        st.error('Username/password is incorrect')
    elif st.session_state.authentication_status == None:
        st.warning('Please enter your username and password')
# --------------------------------------------------------------------------------------------------------

page = st_switcher()
st.markdown("# Prospecção de clientes B2B")

if page == 'yang':
    about()
else:
    app()
    
