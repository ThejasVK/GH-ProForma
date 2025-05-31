import streamlit as st
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split # Though for simple time series, direct indexing is often used
from datetime import datetime, timedelta # timedelta for date manipulations
import os # For directory creation 
import logging
# from datetime import datetime # Requested import, also used by logging implicitly
import pathlib # Requested import
import numpy as np # Requested import
import openpyxl # Essential for pandas to read .xlsx files, requested import
import matplotlib # Requested import (for potential future plotting)
import seaborn as sns # Requested import (for potential future plotting)
import matplotlib.pyplot as plt # For more direct plotting control
 
# --- Configuration ---
LOG_FILE = 'financial_log.txt'
# Key financial statement rows to look for during validation
KEY_ROWS_TO_VALIDATE = ['Total Income', 'Gross Profit', 'Net Ordinary Income', 'Total Expense', 'Net Other Income']
# Expected month abbreviations for column validation
EXPECTED_MONTH_ABBREVIATIONS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
# Minimum number of monthly columns expected (e.g., for a full year)
MIN_MONTHLY_COLUMNS = 12

# --- Logging Setup ---
# Configure logging to append to 'financial_log.txt'
# The format includes timestamp, log level, and the message.
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'  # 'a' for append, 'w' to overwrite each time
)

def get_proper_index_from_row(row_series):
    """
    For a series representing the description columns of a row,
    finds the last non-empty string value to be used as an index.
    """
    last_val = None
    for val in row_series:
        if pd.notna(val):
            cleaned_val = str(val).strip()
            if cleaned_val:  # Ensure it's not an empty string after stripping
                last_val = cleaned_val
    return last_val

def ensure_plots_directory():
    """Ensures that the 'plots' directory exists, creating it if necessary."""
    if not os.path.exists('plots'):
        try:
            os.makedirs('plots')
            logging.info("Created 'plots' directory.")
            print("Debug: Created 'plots' directory.")
        except OSError as e:
            logging.error(f"Error creating 'plots' directory: {e}")
            st.error(f"Could not create 'plots' directory: {e}")
            return False
    return True

def find_header_row_index(excel_file_obj, sheet_name_to_scan):
    """
    Detects the header row index in a given sheet.
    The header row is defined as the first row that is not entirely empty.
    Args:
        excel_file_obj (pd.ExcelFile): The Excel file object.
        sheet_name_to_scan (str): The name of the sheet to scan.
    Returns:
        int: The 0-based index of the header row, or -1 if not found or sheet is empty.
    """
    logging.info(f"Attempting to find header row for sheet: {sheet_name_to_scan}")
    print(f"Debug: Scanning sheet '{sheet_name_to_scan}' for header row...")
    try:
        # Read the sheet without any specific header to inspect all rows
        df_temp = pd.read_excel(excel_file_obj, sheet_name=sheet_name_to_scan, header=None)
        
        if df_temp.empty:
            logging.warning(f"Sheet '{sheet_name_to_scan}' is empty during header detection.")
            print(f"Debug: Sheet '{sheet_name_to_scan}' is empty.")
            return -1

        # Iterate through rows to find the first one that is not entirely NaN
        for i, row_series in df_temp.iterrows():
            if not row_series.isnull().all():
                # This is the first non-empty row.
                logging.info(f"Header row for sheet '{sheet_name_to_scan}' identified at index {i} (0-based).")
                print(f"Debug: Headers for sheet '{sheet_name_to_scan}' (first non-empty row) found at Excel row {i + 1} (1-based).")
                return i # Return the 0-based index of this row
        
        logging.warning(f"No non-empty row found in sheet '{sheet_name_to_scan}'.")
        print(f"Debug: No non-empty row found in sheet '{sheet_name_to_scan}'.")
        return -1
    except Exception as e:
        logging.error(f"Error while trying to find header row for sheet '{sheet_name_to_scan}': {e}")
        print(f"Debug: Error finding header for sheet '{sheet_name_to_scan}': {e}")
        return -1

def validate_dataframe_structure(df, sheet_name_for_validation):
    """
    Validates if the DataFrame contains the required key rows and
    has a valid structure of monthly columns plus a 'TOTAL' column.
    Args:
        df (pd.DataFrame): The DataFrame to validate.
        sheet_name_for_validation (str): The name of the sheet for logging/messaging.
    Returns:
        bool: True if the DataFrame is valid, False otherwise.
    """
    is_structurally_valid = True
    
    # Validate presence of key financial rows
    # These rows are crucial for many financial analyses.
    missing_key_rows = [row_name for row_name in KEY_ROWS_TO_VALIDATE if row_name not in df.index]
    if missing_key_rows:
        warning_msg = f"Sheet '{sheet_name_for_validation}' is missing key financial rows: {', '.join(missing_key_rows)}."
        logging.warning(warning_msg)
        st.warning(warning_msg)
        is_structurally_valid = False

    # Validate monthly columns (e.g., 'Jan 20', 'Feb 20', ..., 'Dec 20') and a 'TOTAL' column
    actual_columns = [str(col).strip() for col in df.columns if pd.notna(col)] # Clean column names
    monthly_cols_count = 0
    found_total_column = 'TOTAL' in actual_columns

    for col_name in actual_columns:
        parts = col_name.split(' ')
        # Check for "Mon YY" format, e.g., "Jan 20"
        if len(parts) == 2 and parts[0] in EXPECTED_MONTH_ABBREVIATIONS and \
           parts[1].isdigit() and len(parts[1]) == 2:
            monthly_cols_count += 1
    
    if not (monthly_cols_count >= MIN_MONTHLY_COLUMNS and found_total_column):
        warning_msg = (f"Sheet '{sheet_name_for_validation}' column structure is invalid: "
                       f"Expected >= {MIN_MONTHLY_COLUMNS} monthly columns (e.g., 'Jan 20') and a 'TOTAL' column. "
                       f"Found: {monthly_cols_count} monthly columns. 'TOTAL' column present: {found_total_column}.")
        logging.warning(warning_msg)
        st.warning(warning_msg)
        is_structurally_valid = False
    
    return is_structurally_valid


def clean_and_transform_dataframe(df_original, sheet_name):
    """
    Cleans the financial data, fills missing values, drops 'TOTAL' column,
    and transforms it into a time-series format with key financial metrics.
    Args:
        df_original (pd.DataFrame): The initially validated DataFrame.
        sheet_name (str): The name of the sheet being processed.
    Returns:
        pd.DataFrame: A cleaned and transformed time-series DataFrame, or None if errors occur.
    """
    df = df_original.copy() # Work on a copy to avoid modifying the original in case of partial failure
    logging.info(f"Starting cleaning and transformation for sheet: {sheet_name}")
    print(f"Debug: Cleaning sheet: {sheet_name}. Initial rows: {df.shape[0]}, Initial columns: {df.columns.tolist()}")

    # 1. Identify monthly columns (exclude 'TOTAL')
    monthly_columns = []
    original_column_names = df.columns.tolist() # Keep original names for indexing df

    for col_name_original in original_column_names:
        col_name_str = str(col_name_original).strip()
        if col_name_str.upper() == 'TOTAL':
            continue
        parts = col_name_str.split(' ')
        if len(parts) == 2 and parts[0] in EXPECTED_MONTH_ABBREVIATIONS and \
           parts[1].isdigit() and len(parts[1]) == 2:
            monthly_columns.append(col_name_original) # Store original name

    if not monthly_columns:
        msg = f"Sheet '{sheet_name}': No valid monthly columns (e.g., 'Jan 20') found for cleaning after initial load. Skipping transformation."
        logging.warning(msg)
        st.warning(msg)
        return None
    logging.info(f"Sheet '{sheet_name}': Identified {len(monthly_columns)} monthly columns for processing: {monthly_columns}")

    # 2. Convert monthly columns to numeric
    coerced_count_total = 0
    for col in monthly_columns: # Iterate using original column names
        # Ensure column exists before trying to convert (it should, as it's from df.columns)
        if col in df.columns:
            original_na_sum = df[col].isna().sum()
            df[col] = pd.to_numeric(df[col], errors='coerce')
            coerced_in_col = df[col].isna().sum() - original_na_sum
            if coerced_in_col > 0:
                logging.warning(f"Sheet '{sheet_name}', column '{col}': {coerced_in_col} values coerced to NaN during numeric conversion.")
                coerced_count_total += coerced_in_col
    if coerced_count_total > 0:
        st.warning(f"Sheet '{sheet_name}': {coerced_count_total} non-numeric values found and converted to NaN in monthly data.")
    print(f"Debug: Sheet '{sheet_name}': Numeric conversion complete. Total values coerced to NaN: {coerced_count_total}")

    # 3. Fill missing values (NaNs)
    missing_filled_count = 0
    for row_name in df.index:
        # Ensure row_name is valid and exists
        if row_name not in df.index: continue

        current_row_data = df.loc[row_name, monthly_columns]
        nan_count_before = current_row_data.isna().sum()

        if nan_count_before == 0: # No NaNs to fill in this row for monthly columns
            continue

        if row_name in KEY_ROWS_TO_VALIDATE: # Key metrics: fill with row mean
            row_mean = current_row_data.mean() # Mean of available numbers in monthly columns for this row
            if pd.notna(row_mean):
                df.loc[row_name, monthly_columns] = current_row_data.fillna(row_mean)
                filled_this_row = nan_count_before - df.loc[row_name, monthly_columns].isna().sum()
                missing_filled_count += filled_this_row
                if filled_this_row > 0:
                    logging.info(f"Sheet '{sheet_name}', key row '{row_name}': Filled {filled_this_row} NaN(s) with mean ({row_mean:.2f}).")
            elif nan_count_before == len(monthly_columns): # All values in the row (for monthly columns) were NaN
                logging.warning(f"Sheet '{sheet_name}', key row '{row_name}': All monthly values are NaN. Cannot compute mean. Row remains NaN. Consider filling with 0 if appropriate.")
                # Optionally, fill with 0 if mean is NaN:
                # df.loc[row_name, monthly_columns] = current_row_data.fillna(0)
                # missing_filled_count += nan_count_before # If you fill with 0
                # logging.info(f"Sheet '{sheet_name}', key row '{row_name}': Filled {nan_count_before} NaN(s) (all were NaN) with 0.")
            else: # Some NaNs, some numbers, but mean resulted in NaN (should be rare)
                logging.warning(f"Sheet '{sheet_name}', key row '{row_name}': Mean calculation resulted in NaN. NaNs not filled by mean.")
        else: # Subcategories: fill with zero
            df.loc[row_name, monthly_columns] = current_row_data.fillna(0)
            missing_filled_count += nan_count_before # All NaNs in subcat rows are filled with 0
            logging.info(f"Sheet '{sheet_name}', sub-category row '{row_name}': Filled {nan_count_before} NaN(s) with 0.")
    
    if missing_filled_count > 0:
        print(f"Debug: Sheet '{sheet_name}': Filled {missing_filled_count} missing values in monthly columns.")
    else:
        print(f"Debug: Sheet '{sheet_name}': No missing values to fill in monthly columns or filling was not applicable.")


    # 4. Drop 'TOTAL' column (if it exists)
    if 'TOTAL' in df.columns:
        df.drop(columns=['TOTAL'], inplace=True, errors='ignore')
        logging.info(f"Sheet '{sheet_name}': Dropped 'TOTAL' column.")
        print(f"Debug: Sheet '{sheet_name}': Dropped 'TOTAL' column.")
    
    # 5. Transform to time-series format
    
    # Check for missing key rows again, as they are essential for the new structure
    missing_essential_rows = [r for r in KEY_ROWS_TO_VALIDATE if r not in df.index]
    if missing_essential_rows:
        err_msg = f"Sheet '{sheet_name}' is missing essential key rows for time-series transformation: {', '.join(missing_essential_rows)}. These rows were expected in the index. Skipping transformation."
        logging.error(err_msg)
        st.error(err_msg)
        return None

    # Check for missing months based on identified monthly_columns (after 'TOTAL' is conceptually excluded)
    if len(monthly_columns) < MIN_MONTHLY_COLUMNS:
        warn_msg = f"Sheet '{sheet_name}' has {len(monthly_columns)} monthly data columns, which is less than the expected {MIN_MONTHLY_COLUMNS}. Time-series will be partial or potentially incomplete."
        logging.warning(warn_msg)
        st.warning(warn_msg)
    
    time_series_data = []
    # Use the filtered 'monthly_columns' list which contains original names of valid month columns
    for month_col_original_name in monthly_columns:
        month_col_cleaned_name = str(month_col_original_name).strip() # For parsing
        try:
            # Parse 'Jan 20' to datetime object 2020-01-01
            date_obj = datetime.strptime(f"01 {month_col_cleaned_name}", "%d %b %y")
        except ValueError as e:
            logging.error(f"Sheet '{sheet_name}': Could not parse date from column name '{month_col_cleaned_name}': {e}. Skipping this column for time-series.")
            continue

        row_data_for_ts = {'Date': date_obj}
        for key_metric in KEY_ROWS_TO_VALIDATE:
            # df.loc should use the original column name from monthly_columns
            value = df.loc[key_metric, month_col_original_name] 
            if pd.isna(value):
                logging.warning(f"Sheet '{sheet_name}', Date '{date_obj.strftime('%Y-%m-%d')}', Metric '{key_metric}': Value is NaN after cleaning. Will be NaN in time-series.")
            row_data_for_ts[key_metric] = value
        
        time_series_data.append(row_data_for_ts)

    if not time_series_data:
        msg = f"Sheet '{sheet_name}': No time-series data could be generated (e.g., all month columns failed parsing or no valid month columns remained)."
        logging.warning(msg)
        st.warning(msg)
        return None

    ts_df = pd.DataFrame(time_series_data)
    
    # Ensure all KEY_ROWS_TO_VALIDATE are columns in ts_df, even if they were all NaN from source
    for key_metric in KEY_ROWS_TO_VALIDATE:
        if key_metric not in ts_df.columns:
            ts_df[key_metric] = pd.NA # Add as a column of NaNs if completely missing (should not happen if logic above is correct)

    ts_df.sort_values(by='Date', inplace=True)
    ts_df.reset_index(drop=True, inplace=True)

    logging.info(f"Sheet '{sheet_name}': Successfully transformed to time-series. Shape: {ts_df.shape}. Columns: {ts_df.columns.tolist()}")
    print(f"Debug: Sheet '{sheet_name}': Time-series DataFrame created. Shape: {ts_df.shape}. Columns: {ts_df.columns.tolist()}")
    
    return ts_df

def generate_proforma_and_visualizations(ts_df, sheet_name, run_timestamp_str):
    """
    Performs proforma analysis using linear regression, calculates financial ratios,
    generates risk flags/recommendations, and creates visualizations.
    Args:
        ts_df (pd.DataFrame): The cleaned time-series DataFrame with key financial metrics.
        sheet_name (str): The name of the sheet being processed.
    Returns:
        pd.DataFrame: A proforma DataFrame with forecasted values and analysis, or None if errors occur.
    """
    logging.info(f"Starting proforma analysis and visualization for sheet: {sheet_name}")
    print(f"Debug: Generating proforma for sheet: {sheet_name}")
    plot_paths = {'line': None, 'bar': None, 'scatter': None} # Initialize plot paths

    if ts_df.empty or len(ts_df) < 2: # Need at least 2 points for regression
        msg = f"Sheet '{sheet_name}': Insufficient data (rows: {len(ts_df)}) for proforma analysis. Skipping."
        logging.warning(msg)
        st.warning(msg)
        return None

    # Ensure 'plots' directory exists
    if not ensure_plots_directory():
        return None # Stop if plot directory cannot be created

    # Prepare data for regression: Convert 'Date' to numerical (e.g., timestamp or ordinal)
    # Using ordinal day number since epoch for simplicity
    ts_df['Date_Ordinal'] = ts_df['Date'].apply(lambda x: x.toordinal())
    
    metrics_to_forecast = ['Total Income', 'Gross Profit', 'Net Ordinary Income', 'Total Expense', 'Net Other Income']
    forecasted_values = {}
    last_historical_predictions = {}
    regression_models = {}

    # Determine next month's date
    last_date = ts_df['Date'].max()
    # Correctly calculate next month: if Dec, next month is Jan of next year
    if last_date.month == 12:
        next_month_date = datetime(last_date.year + 1, 1, 1)
    else:
        next_month_date = datetime(last_date.year, last_date.month + 1, 1)
    
    next_month_ordinal = next_month_date.toordinal()

    for metric in metrics_to_forecast:
        if metric not in ts_df.columns or ts_df[metric].isnull().all():
            logging.warning(f"Sheet '{sheet_name}': Metric '{metric}' is missing or all NaN. Cannot forecast.")
            forecasted_values[metric] = np.nan # Store NaN if metric can't be forecasted
            last_historical_predictions[metric] = np.nan
            continue

        # Drop NaNs for the current metric before fitting
        metric_df = ts_df[['Date_Ordinal', metric]].dropna()
        if len(metric_df) < 2: # Check again after dropping NaNs for specific metric
            logging.warning(f"Sheet '{sheet_name}', Metric '{metric}': Insufficient non-NaN data points ({len(metric_df)}) for regression. Skipping forecast for this metric.")
            forecasted_values[metric] = np.nan
            last_historical_predictions[metric] = np.nan
            continue

        X = metric_df[['Date_Ordinal']]
        y = metric_df[metric]

        model = LinearRegression()
        try:
            model.fit(X, y)
            regression_models[metric] = model # Store the trained model

            # Forecast next month
            predicted_value = model.predict(pd.DataFrame({'Date_Ordinal': [next_month_ordinal]}))[0]
            forecasted_values[metric] = predicted_value
            
            # Predict for the last historical month for scatter plot
            last_historical_ordinal = ts_df['Date_Ordinal'].iloc[-1]
            last_historical_pred = model.predict(pd.DataFrame({'Date_Ordinal': [last_historical_ordinal]}))[0]
            last_historical_predictions[metric] = last_historical_pred

            # Log model metrics
            y_pred_all = model.predict(X)
            mse = mean_squared_error(y, y_pred_all)
            r2 = r2_score(y, y_pred_all)
            logging.info(f"Sheet '{sheet_name}', Metric '{metric}': Regression MSE={mse:.2f}, R²={r2:.2f}")
            print(f"Debug: Sheet '{sheet_name}', Metric '{metric}': Forecasted={predicted_value:.2f}, MSE={mse:.2f}, R²={r2:.2f}")

        except Exception as e:
            logging.error(f"Sheet '{sheet_name}', Metric '{metric}': Error during regression: {e}")
            st.error(f"Error during regression for {metric} on sheet {sheet_name}: {e}")
            forecasted_values[metric] = np.nan
            last_historical_predictions[metric] = np.nan


    # Create Proforma DataFrame
    proforma_data = {'Date': next_month_date}
    proforma_data.update(forecasted_values) # Add all forecasted values (some might be NaN)

    # Calculate Ratios - handle potential NaNs or division by zero
    total_income_forecast = proforma_data.get('Total Income', np.nan)
    total_expense_forecast = proforma_data.get('Total Expense', np.nan)
    net_ordinary_income_forecast = proforma_data.get('Net Ordinary Income', np.nan)

    if pd.notna(total_income_forecast) and pd.notna(total_expense_forecast) and total_income_forecast != 0:
        proforma_data['Expense-to-Income Ratio'] = total_expense_forecast / total_income_forecast
    else:
        proforma_data['Expense-to-Income Ratio'] = np.nan

    if pd.notna(total_income_forecast) and pd.notna(net_ordinary_income_forecast) and total_income_forecast != 0:
        proforma_data['Profit Margin'] = net_ordinary_income_forecast / total_income_forecast
    else:
        proforma_data['Profit Margin'] = np.nan

    # Risk Flags and Recommendations (example logic)
    risk_flags = []
    if pd.notna(proforma_data['Expense-to-Income Ratio']) and proforma_data['Expense-to-Income Ratio'] > 0.8:
        risk_flags.append('High Expenses')
    if pd.notna(net_ordinary_income_forecast) and net_ordinary_income_forecast < 0:
        risk_flags.append('Negative Profit')
    proforma_data['Risk Flags'] = ', '.join(risk_flags) if risk_flags else 'None'

    recommendations = []
    if pd.notna(proforma_data['Profit Margin']) and proforma_data['Profit Margin'] > 0.10 and \
       pd.notna(proforma_data['Expense-to-Income Ratio']) and proforma_data['Expense-to-Income Ratio'] < 0.5:
        recommendations.append('Consider purchase/investment.')
    elif pd.notna(proforma_data['Profit Margin']) and proforma_data['Profit Margin'] < 0.05:
        recommendations.append('Review profitability strategy.')
    proforma_data['Recommendations'] = ', '.join(recommendations) if recommendations else 'Monitor performance.'
    
    proforma_data['Assumptions'] = 'Linear growth based on historical monthly data. Ratios based on forecasted values.'
    
    proforma_df = pd.DataFrame([proforma_data])
    logging.info(f"Sheet '{sheet_name}': Proforma DataFrame generated. Rows: {len(proforma_df)}")
    print(f"Debug: Sheet '{sheet_name}': Proforma rows generated: {len(proforma_df)}")
    
    # --- Visualizations ---
    timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")

    # 1. Line plot of historical and projected metrics
    try:
        plt.figure(figsize=(12, 7))
        for metric in metrics_to_forecast:
            if metric in ts_df.columns and not ts_df[metric].isnull().all(): # Plot historical if available
                plt.plot(ts_df['Date'], ts_df[metric], label=f'Historical {metric}', marker='o', linestyle='-')
            
            # Plot forecasted point if available
            if pd.notna(forecasted_values.get(metric)):
                plt.plot([next_month_date], [forecasted_values[metric]], label=f'Projected {metric}', marker='X', linestyle='--', markersize=10)

        plt.title(f'Historical and Projected Financial Metrics for {sheet_name}')
        plt.xlabel('Date')
        plt.ylabel('Amount')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        # plot_filename = f"plots/{sheet_name}_line_metrics_{timestamp_str}.png"
        # plt.savefig(plot_filename)
        # plt.close()
        # logging.info(f"Sheet '{sheet_name}': Saved line plot to {plot_filename}")
        # print(f"Debug: Creating plot: line_metrics for {sheet_name}")
            # Use run_timestamp_str passed to the function
        plot_paths['line'] = os.path.join('plots', f"{sheet_name}_line_metrics_{run_timestamp_str}.png")
        plt.savefig(plot_paths['line'])
        plt.close()
        logging.info(f"Sheet '{sheet_name}': Saved line plot to {plot_paths['line']}")
        print(f"Debug: Creating plot: line_metrics for {sheet_name} at {plot_paths['line']}")
    except Exception as e:
        logging.error(f"Sheet '{sheet_name}': Error generating line plot: {e}")
        st.warning(f"Could not generate line plot for {sheet_name}: {e}")

    # 2. Bar plot of financial ratios
    try:
        ratios_to_plot = {
            'Expense-to-Income Ratio': proforma_df['Expense-to-Income Ratio'].iloc[0],
            'Profit Margin': proforma_df['Profit Margin'].iloc[0]
        }
        # Filter out NaN ratios for plotting
        ratios_for_plot_data = {k: v for k, v in ratios_to_plot.items() if pd.notna(v)}

        # ADD THESE DEBUG PRINTS FOR BAR PLOT
        print(f"Debug BAR PLOT Data for Sheet '{sheet_name}':")
        print(f"  Proforma DF relevant columns:\n{proforma_df[['Date', 'Total Income', 'Total Expense', 'Net Ordinary Income', 'Expense-to-Income Ratio', 'Profit Margin']]}")
        print(f"  Forecasted TI: {total_income_forecast}, Forecasted TE: {total_expense_forecast}, Forecasted NOI: {net_ordinary_income_forecast}")
        print(f"  Ratios to plot initially: {ratios_to_plot}") # Check this dict
        print(f"  Ratios for plot data (non-NaN): {ratios_for_plot_data}") # Check this dict

        if ratios_for_plot_data: # Only plot if there's valid ratio data
            plt.figure(figsize=(8, 5))
            sns.barplot(x=list(ratios_for_plot_data.keys()), y=list(ratios_for_plot_data.values()))
            plt.title(f'Projected Financial Ratios for {sheet_name} (Next Month)')
            plt.ylabel('Ratio Value')
            # plt.tight_layout()
            # plot_filename = f"plots/{sheet_name}_bar_ratios_{timestamp_str}.png"
            # plt.savefig(plot_filename)
            # plt.close()
            # logging.info(f"Sheet '{sheet_name}': Saved bar plot to {plot_filename}")
            # print(f"Debug: Creating plot: bar_ratios for {sheet_name}")
            plt.tight_layout()
            # Use run_timestamp_str passed to the function
            plot_paths['bar'] = os.path.join('plots', f"{sheet_name}_bar_ratios_{run_timestamp_str}.png")
            plt.savefig(plot_paths['bar'])
            plt.close()
            logging.info(f"Sheet '{sheet_name}': Saved bar plot to {plot_paths['bar']}")
            print(f"Debug: Creating plot: bar_ratios for {sheet_name} at {plot_paths['bar']}")
        else:
            logging.warning(f"Sheet '{sheet_name}': No valid ratio data to plot for bar chart.")
    except Exception as e:
        logging.error(f"Sheet '{sheet_name}': Error generating bar plot: {e}")
        st.warning(f"Could not generate bar plot for {sheet_name}: {e}")

    # 3. Scatter plot of actual vs predicted for the last historical month (if predictions were made)
    try:
        actual_vs_pred_data = []
        # ADD THESE DEBUG PRINTS FOR SCATTER PLOT
        print(f"Debug SCATTER PLOT Data for Sheet '{sheet_name}':")
        print(f"  Last historical predictions: {last_historical_predictions}")
        print(f"  ts_df tail for actual values:\n{ts_df[['Date'] + metrics_to_forecast].tail(2)}")

        for metric in metrics_to_forecast:
            actual_val = ts_df[metric].iloc[-1] if metric in ts_df.columns and not ts_df[metric].empty else np.nan
            pred_val = last_historical_predictions.get(metric, np.nan)
            if pd.notna(actual_val) and pd.notna(pred_val):
                actual_vs_pred_data.append({'Metric': metric, 'Actual': actual_val, 'Predicted': pred_val})
        
        if actual_vs_pred_data:
            scatter_df = pd.DataFrame(actual_vs_pred_data)
            plt.figure(figsize=(8, 6))
            sns.scatterplot(data=scatter_df, x='Actual', y='Predicted', hue='Metric', s=100)
            # Add a y=x line for reference
            min_val = min(scatter_df['Actual'].min(), scatter_df['Predicted'].min())
            max_val = max(scatter_df['Actual'].max(), scatter_df['Predicted'].max())
            plt.plot([min_val, max_val], [min_val, max_val], color='red', linestyle='--')
            plt.title(f'Actual vs. Predicted Values (Last Historical Month) for {sheet_name}')
            plt.xlabel('Actual Value')
            plt.ylabel('Predicted Value (from model fit on historical)')
            plt.grid(True)
            # plt.tight_layout()
            # plot_filename = f"plots/{sheet_name}_scatter_actualvspred_{timestamp_str}.png"
            # plt.savefig(plot_filename)
            # plt.close()
            # logging.info(f"Sheet '{sheet_name}': Saved scatter plot to {plot_filename}")
            # print(f"Debug: Creating plot: scatter_actualvspred for {sheet_name}")
            plt.tight_layout()
            # Use run_timestamp_str passed to the function
            plot_paths['scatter'] = os.path.join('plots', f"{sheet_name}_scatter_actualvspred_{run_timestamp_str}.png")
            plt.savefig(plot_paths['scatter'])
            plt.close()
            logging.info(f"Sheet '{sheet_name}': Saved scatter plot to {plot_paths['scatter']}")
            print(f"Debug: Creating plot: scatter_actualvspred for {sheet_name} at {plot_paths['scatter']}")
                
        else:
            logging.info(f"Sheet '{sheet_name}': No data for actual vs. predicted scatter plot (likely due to missing metrics or failed predictions).")

    except Exception as e:
        logging.error(f"Sheet '{sheet_name}': Error generating scatter plot: {e}")
        st.warning(f"Could not generate scatter plot for {sheet_name}: {e}")
        
    # # Clean up the added 'Date_Ordinal' column from the original ts_df if it was passed around
    # if 'Date_Ordinal' in ts_df.columns: # Should not be needed if ts_df is not modified in place or returned
    #     pass # ts_df is a copy within this scope due to how it's passed or created

    # return proforma_df
    # Clean up the added 'Date_Ordinal' column from the original ts_df if it was passed around
    if 'Date_Ordinal' in ts_df.columns: # Should not be needed if ts_df is not modified in place or returned
        pass # ts_df is a copy within this scope due to how it's passed or created

    return proforma_df, plot_paths # Return plot_paths as well

# ...existing code...
# ...existing code...
def main():
    """
    Main function to run the Streamlit application.
    Handles file upload, processing of Excel sheets, generating financial analysis,
    displaying results in tabs, and saving outputs.
    """
    st.set_page_config(layout="wide")
    st.title("Financial Statement Analyzer")
    logging.info("Application started. Streamlit interface initialized.")
    print("Debug: Application started. Streamlit interface initialized.")

    # File uploader widget for XLSX files
    uploaded_file = st.file_uploader("Upload your Excel workbook (XLSX format)", type=["xlsx"])

    if uploaded_file is not None:
        run_timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S") # Single timestamp for all outputs of this run
        file_name = uploaded_file.name
        logging.info(f"File uploaded: {file_name} (Run Timestamp: {run_timestamp_str})")
        print(f"Debug: Uploaded file: {file_name}")
        st.write(f"**Uploaded file:** `{file_name}`")

        # Dictionary to store valid, cleaned, and transformed DataFrames (time-series)
        processed_timeseries_dataframes = {}
        # Dictionary to store proforma analysis results
        all_proforma_data = {}
        # Dictionary to store plot paths for each sheet
        all_plot_paths = {}
        # List to store names of sheets that are successfully processed for tabs
        valid_sheet_names_for_tabs = []

        try:
            # Use pd.ExcelFile to efficiently access multiple sheets
            excel_file_obj = pd.ExcelFile(uploaded_file)
            sheet_names_from_file = excel_file_obj.sheet_names # Use a different variable name
            logging.info(f"Sheets found in the workbook: {', '.join(sheet_names_from_file)}")
            st.write(f"**Found sheets:** {', '.join(sheet_names_from_file)}")

            for sheet_name in sheet_names_from_file:
                logging.info(f"Processing sheet: {sheet_name}")
                print(f"Debug: Processing sheet: {sheet_name}")
                # Note: st.markdown for individual sheet processing status moved to tabs or removed for cleaner main flow

                # Step 1: Detect the header row for the current sheet
                header_row_idx = find_header_row_index(excel_file_obj, sheet_name)

                if header_row_idx == -1:
                    err_msg = f"Could not determine a valid header row for sheet '{sheet_name}'. Skipping this sheet."
                    logging.warning(err_msg)
                    st.warning(err_msg) # Display warning in Streamlit
                    print(f"Debug: {err_msg}")
                    continue
                
                logging.info(f"Headers for sheet '{sheet_name}' will be read from row index: {header_row_idx} (0-based).")
                print(f"Debug: Headers for sheet '{sheet_name}' found at row: {header_row_idx} (0-based for pd.read_excel).")

                # Step 2: Load data into a pandas DataFrame with hierarchical index
                df_hierarchical = None # Initialize
                try:
                    df_full = pd.read_excel(excel_file_obj, sheet_name=sheet_name, header=header_row_idx)
                    first_data_col_name = None
                    # Try to find the first monthly column
                    for col_name_candidate in df_full.columns:
                        if pd.isna(col_name_candidate): continue
                        col_str = str(col_name_candidate).strip()
                        parts = col_str.split(' ')
                        if len(parts) == 2 and parts[0] in EXPECTED_MONTH_ABBREVIATIONS and \
                           parts[1].isdigit() and len(parts[1]) == 2:
                            first_data_col_name = col_name_candidate
                            break
                    if first_data_col_name is None: # Fallback to 'TOTAL' if no month column found first
                        for col_name_candidate in df_full.columns:
                            if pd.notna(col_name_candidate) and str(col_name_candidate).strip().upper() == 'TOTAL':
                                first_data_col_name = col_name_candidate
                                break
                    if first_data_col_name is None: # Fallback to any column containing a month abbreviation
                        for col_name_candidate in df_full.columns:
                            if pd.isna(col_name_candidate): continue
                            col_str = str(col_name_candidate).strip()
                            if any(month_abbr in col_str for month_abbr in EXPECTED_MONTH_ABBREVIATIONS):
                                first_data_col_name = col_name_candidate
                                break
                                
                    if first_data_col_name is None:
                        err_msg = f"Sheet '{sheet_name}': Could not identify the start of data columns (e.g., monthly columns or 'TOTAL'). Structure might be unexpected. Skipping."
                        logging.warning(err_msg)
                        st.warning(err_msg)
                        print(f"Debug: {err_msg}. Columns found: {df_full.columns.tolist()}")
                        continue

                    first_data_col_loc = df_full.columns.get_loc(first_data_col_name)
                    desc_cols_df = df_full.iloc[:, :first_data_col_loc]
                    data_cols_df = df_full.iloc[:, first_data_col_loc:]
                    new_index = desc_cols_df.apply(get_proper_index_from_row, axis=1)
                    
                    df_hierarchical = data_cols_df.copy()
                    df_hierarchical.index = new_index
                    df_hierarchical.index.name = "Financials"
                    # Clean column names (strip whitespace)
                    df_hierarchical.columns = df_hierarchical.columns.map(lambda x: str(x).strip() if pd.notna(x) else x)
                    # Drop rows where all data columns are NaN AND index is NaN or empty
                    df_hierarchical.dropna(axis=0, how='all', subset=df_hierarchical.columns, inplace=True)
                    df_hierarchical = df_hierarchical[pd.notna(df_hierarchical.index) & (df_hierarchical.index != '')]


                    if df_hierarchical.empty:
                        warning_msg = f"Sheet '{sheet_name}' resulted in an empty DataFrame after hierarchical loading and cleaning (e.g., all rows were empty or index was invalid). Skipping."
                        logging.warning(warning_msg)
                        st.warning(warning_msg)
                        print(f"Debug: {warning_msg}")
                        continue
                    
                    logging.info(f"Successfully loaded hierarchical data for sheet '{sheet_name}'. Shape: {df_hierarchical.shape}")
                    print(f"Debug: Hierarchical DataFrame loaded for sheet '{sheet_name}'. Index head: {df_hierarchical.index[:5].tolist()}")

                except Exception as e:
                    err_msg = f"Error loading or initially processing data from sheet '{sheet_name}': {e}. Skipping."
                    logging.error(err_msg, exc_info=True) # Log full traceback
                    st.error(err_msg)
                    print(f"Debug: {err_msg}")
                    continue
                
                if df_hierarchical is None: # Should be caught by the try-except above
                    logging.error(f"Sheet '{sheet_name}': df_hierarchical is None before validation. This indicates an issue in the loading step. Skipping.")
                    continue

                # Step 3: Validate key rows and monthly column structure
                if validate_dataframe_structure(df_hierarchical, sheet_name):
                    logging.info(f"Sheet '{sheet_name}': Initial structure validation passed.")
                    
                    # Step 4: Clean and transform the validated DataFrame
                    logging.info(f"Attempting to clean and transform sheet: {sheet_name}")
                    print(f"Debug: Cleaning and transforming sheet: {sheet_name}")
                    
                    cleaned_ts_df = clean_and_transform_dataframe(df_hierarchical, sheet_name) 

                    if cleaned_ts_df is not None and not cleaned_ts_df.empty:
                        processed_timeseries_dataframes[sheet_name] = cleaned_ts_df
                        success_msg_clean = f"Sheet '{sheet_name}' cleaned and transformed to time-series successfully."
                        logging.info(success_msg_clean)
                        # st.success(success_msg_clean) # Success message will be part of tab or summary
                        print(f"Debug: {success_msg_clean}. Transformed shape: {cleaned_ts_df.shape}")

                        # Step 5: Generate Proforma Analysis and Visualizations
                        logging.info(f"Attempting proforma analysis for sheet: {sheet_name}")
                        # Pass run_timestamp_str and get plot_paths
                        proforma_df_result, plot_paths_for_sheet = generate_proforma_and_visualizations(cleaned_ts_df, sheet_name, run_timestamp_str)

                        if proforma_df_result is not None and not proforma_df_result.empty:
                            all_proforma_data[f"{sheet_name}_Proforma"] = proforma_df_result
                            all_plot_paths[sheet_name] = plot_paths_for_sheet # Store plot paths
                            valid_sheet_names_for_tabs.append(sheet_name) # Add to list for tab creation
                            success_msg_proforma = f"Sheet '{sheet_name}': Proforma analysis and visualizations generated."
                            logging.info(success_msg_proforma)
                            # st.success(success_msg_proforma) # Success message will be part of tab or summary
                            print(f"Debug: {success_msg_proforma}. Proforma rows: {len(proforma_df_result)}")
                        else:
                            warning_msg_proforma = f"Sheet '{sheet_name}': Proforma analysis could not be completed or generated no data. Plots might also be missing."
                            logging.warning(warning_msg_proforma)
                            st.warning(warning_msg_proforma) # Display warning
                            print(f"Debug: {warning_msg_proforma}")
                            # Even if proforma fails, if cleaned_ts_df exists, we might still want a tab for it.
                            if sheet_name not in valid_sheet_names_for_tabs: # Add if only cleaning was successful
                                valid_sheet_names_for_tabs.append(sheet_name)
                                all_plot_paths[sheet_name] = plot_paths_for_sheet # Store any plots that might have been generated (e.g. line plot if proforma failed later)
                    else:
                        warning_msg_clean = f"Sheet '{sheet_name}' passed initial validation but could not be cleaned/transformed. Skipping further analysis."
                        logging.warning(warning_msg_clean)
                        st.warning(warning_msg_clean) # Display warning
                        print(f"Debug: {warning_msg_clean}")
                else:
                    # validate_dataframe_structure already shows st.warning
                    logging.warning(f"Sheet '{sheet_name}' failed initial structure validation. Skipped.")
                    print(f"Debug: Sheet '{sheet_name}' failed initial structure validation and was skipped.")

            # --- Display results in tabs ---
            if valid_sheet_names_for_tabs:
                st.markdown("--- \n## Analysis Results by Sheet")
                tabs = st.tabs(valid_sheet_names_for_tabs)
                for i, sheet_name_tab in enumerate(valid_sheet_names_for_tabs):
                    with tabs[i]:
                        st.header(f"Analysis for: {sheet_name_tab}")
                        logging.info(f"Rendering tab for sheet: {sheet_name_tab}")
                        print(f"Debug: Rendering tab for sheet: {sheet_name_tab}")

                        # Display Cleaned Time-Series Data
                        if sheet_name_tab in processed_timeseries_dataframes:
                            st.subheader("Cleaned Time-Series Data")
                            st.dataframe(processed_timeseries_dataframes[sheet_name_tab])
                        else:
                            st.warning(f"Cleaned time-series data not available for sheet `{sheet_name_tab}`.")

                        # Display Proforma Data
                        proforma_key = f"{sheet_name_tab}_Proforma"
                        if proforma_key in all_proforma_data:
                            st.subheader("Proforma Analysis (Next Month Forecast)")
                            st.dataframe(all_proforma_data[proforma_key])
                            
                            # Display Recommendations
                            recommendations = all_proforma_data[proforma_key]['Recommendations'].iloc[0]
                            st.subheader("Recommendations")
                            st.write(recommendations if pd.notna(recommendations) and recommendations else "No specific recommendations generated.")
                        else:
                            # Check if it was only cleaned but proforma failed
                            if sheet_name_tab in processed_timeseries_dataframes:
                                st.info(f"Proforma analysis data not generated for sheet `{sheet_name_tab}`.")
                            else: # Should not happen if sheet_name_tab is in valid_sheet_names_for_tabs
                                st.warning(f"Proforma analysis data not available for sheet `{sheet_name_tab}`.")


                        # Display Visualizations
                        st.subheader("Visualizations")
                        plots_available_for_sheet = all_plot_paths.get(sheet_name_tab, {})
                        
                        plot_types_and_captions = {
                            'line': "Historical and Projected Metrics",
                            'bar': "Projected Financial Ratios",
                            'scatter': "Actual vs. Predicted (Last Historical Month)"
                        }

                        any_plot_displayed = False
                        for plot_type, caption in plot_types_and_captions.items():
                            plot_file_path = plots_available_for_sheet.get(plot_type)
                            if plot_file_path and os.path.exists(plot_file_path):
                                try:
                                    st.image(plot_file_path, caption=caption)
                                    logging.info(f"Displaying {plot_type} plot for {sheet_name_tab}: {plot_file_path}")
                                    print(f"Debug: Loading plot: {plot_file_path}")
                                    any_plot_displayed = True
                                except Exception as img_e:
                                    st.warning(f"Could not display {plot_type} plot for {sheet_name_tab} from {plot_file_path}: {img_e}")
                                    logging.error(f"Error displaying {plot_type} plot {plot_file_path} for {sheet_name_tab}: {img_e}")
                            else:
                                # Only log warning if proforma was expected, otherwise it's fine if plot doesn't exist
                                if proforma_key in all_proforma_data or plot_type == 'line': # Line plot might exist even if proforma fails
                                     logging.warning(f"{plot_type} plot file missing or not generated for {sheet_name_tab} at path: {plot_file_path}")
                                     # Don't show st.warning for every missing plot if some are optional
                        if not any_plot_displayed:
                            st.info(f"No visualizations available or generated for sheet `{sheet_name_tab}`.")

            elif uploaded_file: # Check if a file was uploaded but no valid sheets were processed
                st.error("No sheets were successfully processed to display results. Please check the file format, content, and logs.")
                logging.info("No valid sheets processed for tab display from the uploaded file.")

            # --- Save outputs ---
            st.markdown("--- \n## Downloadable Outputs")
            # Save all proforma DataFrames to a single Excel workbook
            if all_proforma_data:
                proforma_excel_filename = f"Proforma_Results_{run_timestamp_str}.xlsx"
                try:
                    with pd.ExcelWriter(proforma_excel_filename, engine='openpyxl') as writer:
                        for proforma_name, df_proforma in all_proforma_data.items():
                            # Sanitize sheet name for Excel (max 31 chars, no invalid chars like ':', '\', '?', '*', '[', ']')
                            safe_sheet_name = "".join(c if c.isalnum() or c in [' ', '_', '-'] else "_" for c in proforma_name)
                            safe_sheet_name = safe_sheet_name[:31] # Ensure length constraint
                            df_proforma.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                    logging.info(f"Successfully saved proforma Excel to: {proforma_excel_filename}")
                    st.success(f"Proforma results saved to `{proforma_excel_filename}`")
                    print(f"Debug: Saving proforma Excel to: {proforma_excel_filename}")
                    # Provide download button for the proforma Excel
                    with open(proforma_excel_filename, "rb") as fp:
                        st.download_button(
                            label="Download Proforma Excel",
                            data=fp,
                            file_name=proforma_excel_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                except Exception as e:
                    logging.error(f"Failed to save proforma Excel '{proforma_excel_filename}': {e}", exc_info=True)
                    st.error(f"Failed to save proforma Excel file: {e}")
            else:
                st.info("No proforma data was generated to save to Excel.")
            
            # Save each cleaned time-series DataFrame as a CSV
            if processed_timeseries_dataframes:
                saved_csv_count = 0
                st.subheader("Cleaned Time-Series CSV Files (Saved Locally)")
                for sheet_name_csv, df_cleaned in processed_timeseries_dataframes.items():
                    # Sanitize sheet name for filename (more restrictive for filenames)
                    safe_csv_sheet_name = "".join(c if c.isalnum() else "_" for c in sheet_name_csv)
                    cleaned_csv_filename = f"{safe_csv_sheet_name}_cleaned_{run_timestamp_str}.csv"
                    try:
                        df_cleaned.to_csv(cleaned_csv_filename, index=False)
                        logging.info(f"Successfully saved cleaned data for '{sheet_name_csv}' to: {cleaned_csv_filename}")
                        print(f"Debug: Saving cleaned CSV for {sheet_name_csv} to: {cleaned_csv_filename}")
                        # st.write(f"- Cleaned data for `{sheet_name_csv}` saved as `{cleaned_csv_filename}`") # Can make UI noisy
                        saved_csv_count +=1
                    except Exception as e:
                        logging.error(f"Failed to save cleaned CSV for '{sheet_name_csv}' to '{cleaned_csv_filename}': {e}", exc_info=True)
                        st.warning(f"Failed to save cleaned CSV for `{sheet_name_csv}`: {e}")
                if saved_csv_count > 0:
                    st.info(f"Cleaned time-series data for {saved_csv_count} sheet(s) saved as CSV files in the application directory.")
                # else: # No need for a message if nothing was saved and processed_timeseries_dataframes was empty
                #    st.info("No cleaned time-series data was available to save as CSV.")
            elif uploaded_file: # Only show if file was uploaded but nothing processed
                 st.info("No cleaned time-series data was generated to save as CSV.")

            logging.info("All processing finished for the uploaded file.")
            print("Debug: End of file processing logic.")

        except Exception as e:
            err_msg = f"A critical error occurred while processing the Excel file: {e}"
            logging.critical(err_msg, exc_info=True) # Log full traceback
            st.error(err_msg)
            print(f"Debug: Critical error during Excel file processing: {e}")

    else:
        st.info("Please upload an Excel (XLSX) file to begin analysis.")

# ...existing code...

if __name__ == "__main__":
    main()
# ...existing code...
