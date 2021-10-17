from ortools.sat.python import cp_model
import pandas as pd
from datetime import datetime

class supplier_allocation:
    """Model which allocates the suppliers in a conference.

    Parameters
    -----------
    steps: list 
        List of (name,transform) tuples

    Attributes
    -----------
    train_col_names: list
        List of column names in input dataframe that is used for training the pipeline
    """
    def __init__(self):
        # Model details
        self.model_name = 'base_model'
        self.model_last_run = datetime.today().strftime('%Y-%m-%d')

        # Global filters
        self.max_suppliers_per_part = 3
        self.max_supplier_capability = 1

        # Parameters for running the model
        self.large_number = 10**6
        self.max_solve_time = 10000
        self.num_search_workers = 8
        self.print_debug = False

        # Parameters for base model
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.allocated_bid = {}
    
    def clean_data(self, products, suppliers, bids):
        '''
            Creates a unique index for all the datasets
            Combines all the supplier and price data to the bids
        '''
        products['prod_index'] = products.index
        suppliers['sup_index'] = suppliers.index
        bids['bid_index'] = bids.index

        complete_data = pd.merge(bids, products,on='prod_name',how='left')
        complete_data = pd.merge(complete_data, suppliers, on = 'supp_name', how = 'left')

        return products, suppliers, bids, complete_data

    def set_constraints(self, kwargs):
        if('max_suppliers' in kwargs):
            self.max_suppliers_per_part = kwargs['max_suppliers']
        if('supplier_capability_limit' in kwargs):
            self.max_supplier_capability = kwargs['supplier_capability_limit']/100

    def build_base_model(self, products, suppliers, bids, complete_data):
        # Integer variables indicating the quantity that has to be allocated to each supplier
        for row in complete_data.iterrows():
            prod_index = row[1].prod_index
            supp_index = row[1].sup_index
            self.allocated_bid[prod_index, supp_index] = \
                self.model.NewIntVar(0, max(products.demand), 'bid_'+ str(prod_index) + '_'+  str(supp_index))
        
        # Total sum allocated should be less than demand
        for p in complete_data.prod_index.unique():
            total_demand_constraint = sum(self.allocated_bid[p, s] for s in \
                complete_data[complete_data.prod_index == p].sup_index.unique()) == \
            products.demand[p]
            self.model.Add(total_demand_constraint)

        # Formulating the objective function
        total_cost = 0
        for row in complete_data.iterrows():
            prod_index = row[1].prod_index
            supp_index = row[1].sup_index
            cost = int(row[1].bid_cost + row[1].other_cost + row[1].trans_cost)
            total_cost += self.allocated_bid[prod_index, supp_index]*cost
        self.model.Minimize(total_cost)

    def add_supplier_capability_constraint(self, products, complete_data):
        # Total sum allocated should be less than demand
        for p in complete_data.prod_index.unique():
            for s in complete_data[complete_data.prod_index == p].sup_index.unique():
                self.model.Add(self.allocated_bid[p, s] <= int(products.demand[p]*self.max_supplier_capability))
    
    def add_maximum_suppliers_per_part(self, complete_data):
        supplier_part_bool = {}
        for p in complete_data.prod_index.unique():
            for s in complete_data[complete_data.prod_index == p].sup_index.unique():
                # if the supplier contribution is greater than zero, then bool should be 1, else 0
                supplier_part_bool[p,s] = self.model.NewBoolVar('supplier_part_bool')
                self.model.Add(self.allocated_bid[p, s] <= supplier_part_bool[p,s]*self.large_number)
            # within a part, the total number of suppliers that have boolean as one is less than the limit
            self.model.Add(sum(supplier_part_bool[p, s] for s in complete_data[complete_data.prod_index == p].sup_index.unique())\
                 <= self.max_suppliers_per_part)

    def solve_model(self):
        self.solver.parameters.max_time_in_seconds = self.max_solve_time
        self.solver.parameters.num_search_workers = self.num_search_workers

        solution_printer = cp_model.ObjectiveSolutionPrinter()
        status = self.solver.SolveWithSolutionCallback(self.model, solution_printer)

        return status
    
    def get_solution_params(self, response = 'obj', status = None):
        if response == 'obj':
            print('Total cost = ', self.solver.ObjectiveValue(), '\n')
            return self.solver.ObjectiveValue()
        elif response == 'stats':
            print(self.solver.ResponseStats())
            return self.solver.ResponseStats()
        elif response == 'status':
            if status == cp_model.OPTIMAL:
                print("OPTIMAL solution")
                return 'optimal'
            elif status == cp_model.FEASIBLE:
                print("FEASIBLE solution (not OPTIMA), probably because of timeout. Take a look above for conflicts")
                return 'feasible'
            elif status == cp_model.INFEASIBLE:
                print('No solution found.')
                return 'infeasible'
            elif status == cp_model.MODEL_INVALID:
                print('Invalid model.')
                return 'invalid'
            elif status == cp_model.UNKNOWN:
                print('Unknown error.')
                return 'error'
            elif status == None:
                print('Status parameter not sent to the model')
    
    def get_solution_data(self, complete_data):
        complete_data['allocation'] = 0
        for i, row in enumerate(complete_data.iterrows()):
            prod_index = row[1].prod_index
            supp_index = row[1].sup_index
            complete_data['allocation'][i] = self.solver.Value(self.allocated_bid[prod_index, supp_index])
        return complete_data[['prod_name', 'supp_name', 'allocation']][complete_data['allocation'] > 0]

    def get_metric(self, complete_data):
        complete_data['total_cost'] = complete_data.bid_cost + complete_data.other_cost + complete_data.trans_cost
        complete_data['total_spends'] = complete_data.total_cost*complete_data.demand

        sum_ = complete_data.groupby('prod_name').aggregate({'total_spends':'mean'}).reset_index()['total_spends'].sum()
        diff_ = self.get_solution_params('obj') - sum_
        return (self.get_solution_params('obj'), int(diff_))
        
    def plot_solution_donut(self, complete_data):
        import matplotlib.pyplot as plt
        f, ax = plt.subplots(figsize=(10, 10))
        complete_data[complete_data.allocation>0].groupby('supp_name').\
            aggregate({'prod_name':'count'}).\
            sort_values('prod_name', ascending = False).\
            plot.pie(y='prod_name', legend=None, rotatelabels=True, 
                    wedgeprops=dict(width=.5), # for donut shape
                    ax = ax
                    )
        plt.ylabel("")
        return f
    
    def plot_bid_heatmap(self, complete_data):
        complete_data['total_cost'] = complete_data.bid_cost + complete_data.other_cost + complete_data.trans_cost
        complete_data['total_spends'] = complete_data.total_cost*complete_data.demand
        prod_list = list(complete_data['prod_name'].unique()) # list of products

        heatmap_data = complete_data[['prod_name', 'supp_name', 'total_cost']].groupby(['supp_name', 'prod_name']).\
            aggregate({'total_cost':'mean'}).unstack().total_cost.rename_axis([None], axis=1).reset_index()
        heatmap_data.index = heatmap_data['supp_name']
        heatmap_data = (heatmap_data-heatmap_data.mean())/heatmap_data.std() # Normalising data

        import seaborn as sns
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=[10,len(heatmap_data)/3.3])
        crest_cmap = sns.color_palette("crest", as_cmap=True)
        sns.heatmap(data=heatmap_data[prod_list], cmap = crest_cmap)
        plt.title("Scaled bid price across suppliers", fontsize=20, y=1.1,loc='left')
        ax.set_ylabel('')
        plt.show()
        return fig
