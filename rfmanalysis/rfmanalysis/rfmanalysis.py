"""Main module."""
import pandas as pd
import numpy as np
import warnings
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')

class RFM:
    """
    It Performs RFM analysis and customer segmentation on the dataset which is input.

    Attributes:
    -----------
    rfm_table : dataframe only with unique customers with their values/scores(rfm)
    segment_table : dataframe with count of customers beyond all segments
    Parameters:
    -----------
    customer_id : string, name of the column that contains the client identification information
    transaction_date : string, the name of the column that contains the transaction date
    amount : string, column that shows the transaction's amount
    automated : bool, default=True, automated execution of operations; pass False if you want to perform each operation manually
    """
    def __init__(self, df:pd.DataFrame, customer_id:str, transaction_date:str, amount:str, automated=True):
        self.df = df
        self.customer_id = customer_id
        self.transaction_date = transaction_date
        self.amount = amount

        if automated:
            df_grp = self.produce_rfm_dateset(self.df)
            df_grp = self.calculate_rfm_score(df_grp)
            self.rfm_table = self.find_segments(df_grp)
            self.segment_table = self.find_segment_df(self.rfm_table)

    def produce_rfm_dateset(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        produce_rfm_dataset(df)
        |
        |  This function produces a dataframe object after locating RFM values for the dataset entered.
        |  The functionality consists of preprocessing, grouping by customer_id, finding RFM values.
        |
        |  Parameters:
        |  -----------
        |  df : pd.DataFrame object, holding raw transaction records of customers
        |
        |   Returns
        |   -------
        |       DataFrame object
        """
        for i in df.columns:
            if i != self.customer_id:
                df[i] = df[i].astype(str).apply(lambda x: x.strip()[:-2] if '.0' in x else x.strip())
            if 'date' in i.lower():
                df[i] = pd.to_datetime(df[i])

        df = df.sort_values(by=self.transaction_date, na_position='first')
        df[self.amount] = df[self.amount].apply(lambda x: float(x) if x not in ['', 'nan'] else 0)
        df = df.dropna(subset=[self.customer_id, self.amount])
        df = df.drop_duplicates()
        df = df.reset_index().drop(columns=['index'], axis=1)
        df[self.customer_id] = df[self.customer_id].astype(str).apply(
            lambda i: i.strip()[:-2] if '.0' in i else i.strip())

        # grouping by customer_id
        df_grp = df[[self.customer_id, self.transaction_date, self.amount]].groupby(self.customer_id, ).agg(
            list).reset_index()

        # finding r,f,m values

        latest_date = df[self.transaction_date].max()
        df_grp['recency'] = df_grp[self.transaction_date].apply(lambda i: (latest_date - i[-1]).days)
        df_grp['frequency'] = df_grp[self.amount].apply(len)
        df_grp['monetary_value'] = df_grp[self.amount].apply(sum)

        return df_grp[[self.customer_id, 'recency', 'frequency', 'monetary_value']]

        # This adds functionality for dynamic binning

    def dynamic_cutoffs(self, df, column, n_bins=5):
        """
        dynamic_cutoffs(df, column, n_bins)
        |
        |  This function calculates dynamic cutoffs for r,f,m values.
        |  which are consumed by "calculate_dynamic_rfm_score" function internally.
        |
        |  Here there is used dynamic cutoffs for binning customers
        |  into rfm scores in a more sensible way
        |  better than using static cutoffs.
        |
        |
        |  Parameters:
        |  -----------
        |  df : pd.DataFrame object
        |  column : str, name of columns for binning
        |  n_bins : int, no. of bins to perform
        |
        |   Returns
        |   -------
        |       rfm_cutoffs : dict
        """
        df2 = pd.DataFrame()
        examples = 100
        d = df[column].quantile([i / 100 for i in range(1, 101)]).to_dict()
        d = pd.DataFrame({'%': d.keys(), column: d.values()})
        while (n_bins > 1):
            cutoff_percentile = d.iloc[int(examples / n_bins)][column]
            mask = d[column] <= cutoff_percentile
            d.loc[mask, 'bin_no'] = n_bins
            new_index = d[d['bin_no'].isna()].index[0]
            dd = pd.concat([df2, d[d['bin_no'].notna()]], axis=0).reset_index().drop('index', axis=1)
            d = d.iloc[new_index:].reset_index().drop('index', axis=1)
            examples = len(d)
            n_bins = n_bins - 1
            if n_bins == 1:
                break
        d['bin_no'] = n_bins
        dd = pd.concat([df2, d[d['bin_no'].notna()]], axis=0).reset_index().drop('index', axis=1)
        dd = dd.groupby('bin_no').agg(list).reset_index()
        rfm_cutoffs = dict()
        for i in dd['bin_no'] - 1:
            rfm_cutoffs[i + 1] = [min(dd[column][i]), max(dd[column][i])]
        if column == 'recency':
            return rfm_cutoffs
        else:
            rc = dict()
            for e in range(1, len(rfm_cutoffs) + 1):
                rc[len(rfm_cutoffs) - e + 1] = rfm_cutoffs[e]
            return rc

    def find_bin_no(self, x, col, cutoff):
        """
        find_bin_no(x, col, cutoff)
        |
        |  This function helps to apply on a column to find bin numbers of respective column values
        |
        |
        |  Parameters:
        |  -----------
        |  x : input value for that record instance
        |  col : str, column name
        |  cutoff : dict, rfm_cutoff generated from dynamic_cutoffs & adjust_cutoffs
        |
        |   Returns
        |   -------
        |       k : int, bin number for respective input
        """
        for i in cutoff:
            if cutoff[0] <= x <= cutoff[i][1]:
                return i

    def adjust_cutoffs(self, df, cutoff, col):
        """
        adjust_cutoffs(df, cutoff, col)
        |
        |  This function is created to adjust the threshold values of bins
        |  in an edge-to-edge fashion thus avoiding generation of any NA values.
        |
        |
        |  Parameters:
        |  -----------
        |  df : pd.DataFrame object, local instance of dataframe
        |  cutoff : dict, rfm_cutoff generated from dynamic_cutoffs & adjust_cutoffs
        |  col : str, name of column
        |
        |   Returns
        |   -------
        |       cutoff : dict, adjusted rfm cutoffs for binning purpose
        """
        if col == 'recency':
            cutoff[5][0] = df['recency'].min()
            cutoff[5][1] = cutoff[4][0] - 1e-4
            cutoff[4][1] = cutoff[3][0] - 1e-4
            cutoff[3][1] = cutoff[2][0] - 1e-4
            cutoff[2][1] = cutoff[1][0] - 1e-4
            cutoff[1][1] = df['recency'].max()
        else:
            cutoff[5][1] = df[col].max()
            cutoff[4][1] = cutoff[5][0] - 1e-4
            cutoff[3][1] = cutoff[4][0] - 1e-4
            cutoff[2][1] = cutoff[3][0] - 1e-4
            cutoff[1][1] = cutoff[2][0] - 1e-4
            cutoff[1][0] = df[col].min()
        return cutoff

    def calculate_dynamic_rfm_score(self, df, n_bins):
        """
        calculate_dynamic_rfm_score(df, n_bins)
        |
        |  This function dynamically calculates recency, frequency and monetary scores (binning) and puts into columns
        |  of master dataframe.
        |
        |  Parameters:
        |  -----------
        |  df : pd.DataFrame object, local instance of dataframe
        |  n_bins : number of bins for binning
        |
        |   Returns
        |   -------
        |       df : pd.DataFrame, with added rfm score columns: r, f, m, rfm
        """
        """

        """
        recency_coffs = self.adjust_cutoffs(df, self.dynamic_cutoffs(df, 'recency', n_bins), 'recency')
        frequency_coffs = self.adjust_cutoffs(df, self.dynamic_cutoffs(df, 'frequency', n_bins), 'frequency')
        monetary_coffs = self.adjust_cutoffs(df, self.dynamic_cutoffs(df, 'monetary_value', n_bins), 'monetary_value')

        df['r'] = df['recency'].apply(lambda x: int(self.find_bin_no(x, 'recency', recency_coffs)))
        df['f'] = df['frequency'].apply(lambda x: self.find_bin_no(x, 'frequency', frequency_coffs))
        df['m'] = df['monetary_value'].apply(lambda x: self.find_bin_no(x, 'monetary_value', monetary_coffs))
        df['rfm_score'] = df['r'].apply(str) + df['f'].apply(str) + df['m'].apply(str)
        return df

    def calculate_rfm_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        calculate_rfm_score(df)
        |
        |  This function calculates rfm scores based on rfm values (binning)
        |
        |  Parameters:
        |  -----------
        |  df : pd.DataFrame object, containing recency, frequency and monetary_value columns
        |
        |  Returns
        |  -------
        |  df : pd.DataFrame object
        """
        df['r'] = pd.qcut(df['recency'].rank(method='first'), 5, labels=[5, 4, 3, 2, 1]).tolist()
        df['f'] = pd.qcut(df['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).tolist()
        df['m'] = pd.qcut(df['monetary_value'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).tolist()
        df['rfm_score'] = df['r'].apply(str) + df['f'].apply(str) + df['m'].apply(str)
        df = df.sort_values(by='rfm_score', ascending=False).reset_index(drop=True)
        return df

    def find_segments(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        find_segments(df)
        |
        |  This function finds customer segments based on the rfm scores.
        |
        |  Parameters:
        |  -----------
        |  df : pd.DataFrame object, containing r,f,m scores columns
        |
        |  Returns
        |  -------
        |  df : pd.DataFrame object
        """
        classes = []
        classes_append = classes.append
        customers_ = self.customer_id
        for row in df.iterrows():
            rec = row[1]
            r = rec['r']
            f = rec['f']
            m = rec['m']
            if (r in (4, 5)) & (f in (4, 5)) & (m in (4, 5)):
                classes_append({rec[customers_]: 'Champions'})
            elif (r in (4, 5)) & (f in (1, 2)) & (m in (3, 4, 5)):
                classes_append({rec[customers_]: 'Promising'})
            elif (r in (3, 4, 5)) & (f in (3, 4, 5)) & (m in (3, 4, 5)):
                classes_append({rec[customers_]: 'Loyal Accounts'})
            elif (r in (3, 4, 5)) & (f in (2, 3)) & (m in (2, 3, 4)):
                classes_append({rec[customers_]: 'Potential Loyalist'})
            elif (r in (5,)) & (f in (1,)) & (m in (1, 2, 3, 4, 5)):
                classes_append({rec[customers_]: 'New Active Accounts'})
            elif (r in (3, 4, 5)) & (f in (1, 2, 3, 4, 5)) & (m in (1, 2)):
                classes_append({rec[customers_]: 'Low Spenders'})
            elif (r in (2, 3)) & (f in (1, 2)) & (m in (4, 5)):
                classes_append({rec[customers_]: 'Need Attention'})
            elif (r in (2, 3)) & (f in (1, 2)) & (m in (1, 2, 3)):
                classes_append({rec[customers_]: "About to Sleep"})
            elif (r in (1, 2)) & (f in (1, 2, 3, 4, 5)) & (m in (3, 4, 5)):
                classes_append({rec[customers_]: 'At Risk'})
            elif (r in (1, 2)) & (f in (1, 2, 3, 4, 5)) & (m in (1, 2)):
                classes_append({rec[customers_]: "Lost"})
            else:
                classes.append({0: [row[1]['r'], row[1]['f'], row[1]['m']]})
        accses = [list(i.keys())[0] for i in classes]
        segments_ = [list(i.values())[0] for i in classes]
        df['segment'] = df[self.customer_id].map(dict(zip(accses, segments_)))
        return df

    def find_segment_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        find_segment_df(df)
        |
        |  This function returns segment distribution dataset.
        |
        |  Parameters:
        |  -----------
        |  df : pd.DataFrame, rfm_table, result from find_segments function
        |
        |  Returns segment distribution dataframe
        """
        segmented_df = df[['segment', self.customer_id]].groupby('segment', sort=False).count().reset_index().rename(
            {self.customer_id: 'no of customers'}, axis=1)
        return segmented_df

    def find_customers(self, segment: str) -> pd.DataFrame:
        """
        find_customers(segment)
        |
        |  This function returns dataframe of entered segment.
        |
        |  Parameters:
        |  ----------
        |  segment : str, one of the 10 categories : ['Champions', 'Loyal Accounts', 'Low Spenders', 'Potential Loyalist', 'Promising', 'New Active Accounts', 'Need Attention', 'About to Sleep', 'At Risk', 'Lost']
        |
        |  Returns dataframe of customers with specified segment
        """
        return self.rfm_table[self.rfm_table['segment'] == segment].reset_index(drop=True)

    def plot_column_distribution(self, column: str, figsize=(10, 5)):
        """
        plot_column_distribution(col, figsize)
        |
        |  This plot shows distribution of entered column
        |
        |  Parameters:
        |  -----------
        |  column : str, column name
        |  figsize : (x,y) size of the figure; default = (10,5)
        |
        |  Returns None
        """
        plt.figure(figsize=figsize)
        plt.hist(self.rfm_table[column], edgecolor='black')
        plt.grid()
        plt.xlabel(column.capitalize())
        plt.ylabel('Count')
        plt.title(column.capitalize())
        plt.show()

    def plot_versace_plot(self, column1: str, column2: str, figsize=(10, 7)):
        """
        plot_versace_plot(column1, column2, figsize)
        |
        |  This plot shows scatter plot of columns col1 vs col2.
        |
        |  Parameters:
        |  -----------
        |  column1 : str, column 1 name
        |  column2 : str, column 2 name
        |
        |  figsize : (x,y) size of the figure; default = (10,7)
        |
        |  Returns None
        """
        plt.figure(figsize=figsize)
        plt.scatter(self.rfm_table[column1], self.rfm_table[column2])
        plt.xlabel(column1.capitalize())
        plt.ylabel(column2.capitalize())
        plt.title(f'{column1.capitalize()} vs {column2.capitalize()}')
        plt.grid()
        plt.show()

    def plot_segment_distribution(self):
        """
        plot_segment_distribution()
        |
        |  This plot shows the number of customers across all segments.
        |
        |  Parameters: None
        |
        |  Returns None
        """
        x = self.segment_table['segment'][::-1]
        y = self.segment_table['no of customers'][::-1]
        plt.figure(figsize=(8, 5))
        plt.barh(x, y, color=['#ec008c', '#68217a', '#00188f', '#00bcf2', '#00b294', '#009e49', '#bad80a', '#fff100',
                              '#ff8c00', '#e81123'], edgecolor='black')
        plt.xlabel('Number of Customers')
        plt.ylabel('The Segment')
        plt.title('The Segment Distribution')
        plt.grid()
        plt.show()

    def plot_distribution_by_segment(self, column: str, take='median'):
        """
        plot_distribution_by_segment(column, take)
        |
        |  This plot shows mean and median distribution of column by segment.
        |
        |  Parameters:
        |  -----------
        |  column : str, column name
        |  take : str, mean or median; include whichever required
        |
        |  Returns None
        """
        median_ = self.rfm_table.groupby('segment', sort=False)[column].agg(lambda x: list(x)).reset_index()
        if take == 'median':
            median_[column] = median_[column].apply(np.median)
        if take == 'mean':
            median_[column] = median_[column].apply(np.mean)
        x = median_['segment'][::-1]
        y = median_[column][::-1]
        plt.figure(figsize=(8, 5))
        plt.barh(x, y, color=['#ec008c', '#68217a', '#00188f', '#00bcf2', '#00b294', '#009e49', '#bad80a', '#fff100',
                              '#ff8c00', '#e81123'], edgecolor='black')
        plt.xlabel(f'{take} {column.capitalize()}')
        plt.ylabel('Segment')
        plt.title(f'{take} {column.capitalize()} by Segment')
        plt.grid()
        plt.show()

    def plot_rfm_histograms(self):
        """
        plot_rfm_histograms()
        |
        | This plot shows histograms of recency, frequency and monetary.
        |
        |  Parameters: None
        |
        |  Returns None
        """
        fig, axs = plt.subplots(1, 3)
        fig.set_figheight(5)
        fig.set_figwidth(15)
        fig.suptitle('RFM Distributions')
        axs[0].hist(self.rfm_table['recency'], edgecolor='black')
        axs[0].set_title('Recency')
        axs[1].hist(self.rfm_table['frequency'], edgecolor='black')
        axs[1].set_title('Frequency')
        axs[2].hist(self.rfm_table['monetary_value'], edgecolor='black')
        axs[2].set_title('Monetary Value')
        plt.show()

    def plot_rfm_order_distribution(self):
        """
        plot_rfm_order_distribution()
        |
        |  This plot shows number of customers vs number of orders.
        |
        |  Parameters: None
        |
        |  Returns None
        """
        d = self.rfm_table.groupby('frequency').count().reset_index()
        x = d['frequency']
        y = d[self.customer_id]
        plt.figure(figsize=(15, 7))
        plt.bar(x, y)
        plt.xlabel('Orders')
        plt.ylabel('Customers')
        plt.title('Customers by Orders')
        plt.grid()
        plt.show()
