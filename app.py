import streamlit as st
import time
import numpy as np
import pandas as pd

from supplier_allocation import supplier_allocation

st.sidebar.markdown("## Constraints")
max_suppliers = st.sidebar.selectbox(
    'Maximum number of suppliers that can be awarded some proportion of the demand for a part.',
    options = [1,2,3,4], index = 1)
supplier_capability_limit = st.sidebar.slider(
    'Maximum percentage of demand of  part that can be allocated to a supplier.',
    value = 80, min_value = 0, max_value = 100)

def load_sample_data(type):
    if(type == 'products'):
        return pd.read_csv('sample_data/products.csv')
    elif(type == 'suppliers'):
        return pd.read_csv('sample_data/suppliers.csv')
    elif(type == 'bids'):
        return pd.read_csv('sample_data/bids.csv')

# products, suppliers, bids = load_sample_data()
"""
# Bid Allocation
**Author: Achyuthuni Sri Harsha** [www.harshaash.website](https://www.harshaash.website/)  
This is an application that recieves bids and gives the most optimal selection of bids. There are various filters and constraints that can be applied.  
At the backend, it runs a linear/integer optimiser using Google's ORTools. This tool is built using streamlit.  
You will need to provide the details of products, suppliers and the bids. This can be done either by uploading *csv files* with the same column names or by modifying the data below.  
___

## Input
Modify the below data as it suits your use case:

### Products
Variables:
- prod_name: Name of the product that has to be bought/sold  
- prod_desc(optional): A one line description of the product  
- selling_price (0 is not applicable): The price at which the item is sold in the market (0 if not used)  
- demand: The total demand or requirement of the product  
"""
prod_file = st.file_uploader(label = 'Load a csv file with the columns as above', type = ['csv'], key = 0)
if prod_file  is not None:
    products = pd.read_csv(prod_file)
    # TODO
else:
    products = load_sample_data('products')
st.write(products)
"""
### Suppliers
Variables:
- supp_name: Name of the supplier/buyer  
- supp_desc (optional): Description of the supplier  
- trans_cost (0 is not applicable): The transportation cost for this supplier  

"""
supp_file = st.file_uploader(label = 'Load a csv file with the columns as above', type = ['csv'], key = 1)
if supp_file  is not None:
    suppliers = pd.read_csv(supp_file)
    # TODO
else:
    suppliers = load_sample_data('suppliers')
st.write(suppliers)
"""
### Bids
Variables:
- prod_name: Product name which is same as in the product table  
- supp_name: Supplier name which is same as supplier table  
- bid_cost: The price quoted by the supplier for the product  
 - other-cost: Other costs incurred for supplying/delivering the part by/to the supplier  

"""
bids_file = st.file_uploader(label = 'Load a csv file with the columns as above', type = ['csv'], key = 2)
if bids_file  is not None:
    bids = pd.read_csv(bids_file)
    # TODO
else:
    bids = load_sample_data('bids')
st.write(bids)
"""
After finishing the uploading of the data, press the below button for getting the optimal results.  
"""
st.button("Re-run")
"""
___
## Output
For large problems, please give us a minute for calculating the output.  
"""

# Code for supplier allocations
model = supplier_allocation()
products, suppliers, bids, complete_data = model.clean_data(products, suppliers, bids)
model.set_constraints({'max_suppliers':max_suppliers, 'supplier_capability_limit':supplier_capability_limit})
model.build_base_model(products, suppliers, bids, complete_data)
# implement the additional constraints
model.add_supplier_capability_constraint(products, complete_data)
model.add_maximum_suppliers_per_part(complete_data)
# run the solver
status = model.solve_model()
if(model.get_solution_params('status', status) in ['optimal', 'feasible']):
    # Get results if the solution is optimal
    result = model.get_solution_data(complete_data)
    st.write('The optimal solution is as follows')
    st.write(result)
    st.markdown("""
    ### Analysis of the result
    The proportion of the number of bids awarded to each supplier
    """)
    st.pyplot(model.plot_solution_donut(result))
    st.metric('Total cost', *model.get_metric(complete_data), delta_color="inverse")
else:
    st.write('There is no solution to the problem. Please refine your constraints or check your data.')
