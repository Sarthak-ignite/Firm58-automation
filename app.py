import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def load_and_process_firm58_data(file):
    df = pd.read_csv(file)
    columns_to_extract = ['Quantity', 'Contra Firm', 'Algo Fee', 'Exec Fees', 'Contra Firm Route']
    extracted_df = df[columns_to_extract]
    extracted_df['Quantity'] = pd.to_numeric(extracted_df['Quantity'].replace(',', '', regex=True), errors='coerce')
    extracted_df['Algo Fee'] = pd.to_numeric(extracted_df['Algo Fee'].replace(',', '', regex=True), errors='coerce')
    extracted_df['Contra Firm'] = extracted_df['Contra Firm'].astype(str)
    extracted_df['Contra Firm'].replace('nan', None, inplace=True)
    extracted_df = extracted_df.rename(columns={'Contra Firm Route': 'Liquidity'})
    return extracted_df

def load_and_process_guzzman_data(file):
    df = pd.read_csv(file)
    df.columns = df.columns.str.strip()
    columns_to_extract = ['Exchange', 'Quantity', 'Passed Exchange Transaction Fees', 'Exec Fees', 'Liquidity']
    extracted_df = df[columns_to_extract]
    return extracted_df

def process_and_compare_data(firm58_df, guzzman_df):
    mapping = {
        'XASE': 'AMEX', 'ARCX': 'ARCA', 'BATS': 'BATS', 'BATY': 'BATS-BYX',
        'HRTF': 'BROKER TRADES - HRTF', 'INTL': 'BROKER TRADES - INTL',
        'EDGA': 'EDGA', 'EDGX': 'EDGX', 'EDDP': 'EDGX', 'IEXD': 'IEX',
        'IEXG': 'IEX', 'BAML': 'INTERNAL CROSSING', 'MEMX': 'MEMX',
        'EPRL': 'MIAX', 'NASD': 'NASDAQ', 'XNAS': 'NASDAQ', 'KNLI': 'NITE',
        'XBOS': 'NQBX', 'XNYS': 'NYSE', 'NYSD': 'NYSE', 'XCIS': 'NYSE National'
    }
    
    exchanges_to_modify = ['BATS', 'BATS-BYX', 'BROKER TRADES - INTL', 'EDGA', 'EDGX']
    
    firm58_df.loc[firm58_df['Contra Firm'].replace(mapping).isin(exchanges_to_modify), 'Liquidity'] = 'Consolidated'
    guzzman_df.loc[guzzman_df['Exchange'].replace(mapping).isin(exchanges_to_modify), 'Liquidity'] = 'consolidated'
    
    firm58_grouped = firm58_df.groupby(['Contra Firm', 'Liquidity']).agg({
        'Quantity': 'sum',
        'Algo Fee': 'sum',
        'Exec Fees': 'sum'
    }).reset_index()
    
    firm58_grouped['Contra Firm'] = firm58_grouped['Contra Firm'].replace(mapping)
    firm58_grouped = firm58_grouped.groupby(['Contra Firm', 'Liquidity']).agg({
        'Quantity': 'sum',
        'Algo Fee': 'sum',
        'Exec Fees': 'sum'
    }).reset_index()
    
    firm58_grouped = firm58_grouped.rename(columns={
        'Algo Fee': 'Passed Exchange Transaction Fees',
        'Contra Firm': 'Exchange'
    })
    
    guzzman_grouped = guzzman_df.groupby(['Exchange', 'Liquidity']).agg({
        'Quantity': 'sum',
        'Passed Exchange Transaction Fees': 'sum',
        'Exec Fees': 'sum'
    }).reset_index()
    
    comparison_df = firm58_grouped.merge(guzzman_grouped, on=['Exchange', 'Liquidity'], suffixes=('_firm58', '_Guzzman'))
    
    comparison_df['Quantity Discrepancy'] = comparison_df['Quantity_firm58'] - comparison_df['Quantity_Guzzman']
    comparison_df['Passed Exchange Transaction Fees Discrepancy'] = comparison_df['Passed Exchange Transaction Fees_firm58'] - comparison_df['Passed Exchange Transaction Fees_Guzzman']
    comparison_df['Exec Fees Discrepancy'] = comparison_df['Exec Fees_firm58'] - comparison_df['Exec Fees_Guzzman']
    
    return comparison_df, firm58_df, guzzman_df

def create_discrepancy_plots(comparison_df):
    fig = make_subplots(rows=3, cols=1, 
                        subplot_titles=("Quantity Discrepancy", 
                                        "Passed Exchange Transaction Fees Discrepancy", 
                                        "Exec Fees Discrepancy"),
                        vertical_spacing=0.1)

    fig.add_trace(
        go.Bar(x=comparison_df['Exchange'], 
               y=comparison_df['Quantity Discrepancy'],
               name="Quantity",
               hovertext=comparison_df['Liquidity']),
        row=1, col=1
    )

    fig.add_trace(
        go.Bar(x=comparison_df['Exchange'], 
               y=comparison_df['Passed Exchange Transaction Fees Discrepancy'],
               name="Transaction Fees",
               hovertext=comparison_df['Liquidity']),
        row=2, col=1
    )

    fig.add_trace(
        go.Bar(x=comparison_df['Exchange'], 
               y=comparison_df['Exec Fees Discrepancy'],
               name="Exec Fees",
               hovertext=comparison_df['Liquidity']),
        row=3, col=1
    )

    fig.update_layout(height=1200, width=800, title_text="Discrepancies by Exchange")
    fig.update_xaxes(tickangle=45)

    return fig

def main():
    st.title("Trade Report Comparison Dashboard")
    
    firm58_file = st.file_uploader("Upload Firm58 CSV file", type="csv")
    guzzman_file = st.file_uploader("Upload Guzzman CSV file", type="csv")
    
    if firm58_file and guzzman_file:
        firm58_df = load_and_process_firm58_data(firm58_file)
        guzzman_df = load_and_process_guzzman_data(guzzman_file)
        
        comparison_df, firm58_processed, guzzman_processed = process_and_compare_data(firm58_df, guzzman_df)
        
        st.subheader("Comparison Results")
        st.dataframe(comparison_df)
        
        st.subheader("Discrepancies Visualization")
        fig = create_discrepancy_plots(comparison_df)
        st.plotly_chart(fig)
        
        # Summary statistics
        st.subheader("Summary Statistics")
        total_quantity_discrepancy = comparison_df['Quantity Discrepancy'].abs().sum()
        total_fees_discrepancy = comparison_df['Passed Exchange Transaction Fees Discrepancy'].abs().sum()
        total_exec_fees_discrepancy = comparison_df['Exec Fees Discrepancy'].abs().sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Quantity Discrepancy", f"{total_quantity_discrepancy:.2f}")
        col2.metric("Total Fees Discrepancy", f"${total_fees_discrepancy:.2f}")
        col3.metric("Total Exec Fees Discrepancy", f"${total_exec_fees_discrepancy:.2f}")
        
        # Identify largest discrepancies
        st.subheader("Largest Discrepancies")
        largest_quantity = comparison_df.loc[comparison_df['Quantity Discrepancy'].abs().idxmax()]
        largest_fees = comparison_df.loc[comparison_df['Passed Exchange Transaction Fees Discrepancy'].abs().idxmax()]
        largest_exec_fees = comparison_df.loc[comparison_df['Exec Fees Discrepancy'].abs().idxmax()]
        
        st.write(f"Largest Quantity Discrepancy: {largest_quantity['Exchange']} ({largest_quantity['Liquidity']}) - {largest_quantity['Quantity Discrepancy']:.2f}")
        st.write(f"Largest Fees Discrepancy: {largest_fees['Exchange']} ({largest_fees['Liquidity']}) - ${largest_fees['Passed Exchange Transaction Fees Discrepancy']:.2f}")
        st.write(f"Largest Exec Fees Discrepancy: {largest_exec_fees['Exchange']} ({largest_exec_fees['Liquidity']}) - ${largest_exec_fees['Exec Fees Discrepancy']:.2f}")
        
        # Download options
        st.subheader("Download Results")
        comparison_csv = comparison_df.to_csv(index=False)
        st.download_button(
            label="Download comparison CSV",
            data=comparison_csv,
            file_name="comparison_results.csv",
            mime="text/csv",
        )
        
        # Identify and save discrepancies
        discrepancy_mask = (
            (comparison_df['Quantity Discrepancy'] != 0) |
            (comparison_df['Passed Exchange Transaction Fees Discrepancy'] != 0) |
            (comparison_df['Exec Fees Discrepancy'] != 0)
        )
        discrepancies = comparison_df[discrepancy_mask]
        
        firm58_discrepancies = firm58_processed[
            firm58_processed.apply(lambda row: (row['Contra Firm'] in discrepancies['Exchange'].values) and
                                               (row['Liquidity'] in discrepancies['Liquidity'].values), axis=1)
        ]
        guzzman_discrepancies = guzzman_processed[
            guzzman_processed.apply(lambda row: (row['Exchange'] in discrepancies['Exchange'].values) and
                                                (row['Liquidity'] in discrepancies['Liquidity'].values), axis=1)
        ]
        
        firm58_csv = firm58_discrepancies.to_csv(index=False)
        guzzman_csv = guzzman_discrepancies.to_csv(index=False)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="Download Firm58 Discrepancies",
                data=firm58_csv,
                file_name="firm58_discrepancies.csv",
                mime="text/csv",
            )
        with col2:
            st.download_button(
                label="Download Guzzman Discrepancies",
                data=guzzman_csv,
                file_name="guzzman_discrepancies.csv",
                mime="text/csv",
            )

if __name__ == "__main__":
    main()