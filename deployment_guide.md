# Deployment Guide for Financial Analysis App

## Local Setup and Testing
1. **Install Python 3.8+**: Download from python.org.
2. **Create Virtual Environment**:
   - Linux/Mac: `python -m venv financial_env; source financial_env/bin/activate`
   - Windows: `python -m venv financial_env; financial_env\Scripts\activate`
3. **Install Dependencies**: `pip install pandas openpyxl numpy scikit-learn matplotlib seaborn streamlit`
4. **Save Dependencies**: `pip freeze > requirements.txt`
5. **Run Locally**: `streamlit run app.py`
   - Open browser at `http://localhost:8501`
   - Upload an Excel file and verify results (data, plots, proforma).
6. **Debugging**: Check `financial_log.txt` for errors and console for print statements.

## Deployment to Streamlit Cloud
1. **Create Git Repository**:
   - `git init`
   - `git add app.py requirements.txt`
   - `git commit -m "Initial commit"`
2. **Push to GitHub**: Create a repository on GitHub and push: `git remote add origin <url>; git push origin main`
3. **Deploy on Streamlit Cloud**:
   - Sign up at share.streamlit.io.
   - Create a new app, link to your GitHub repository, and select `app.py`.
   - Ensure `requirements.txt` is included.
   - Deploy and test the app URL.

## Deployment to Heroku
1. **Install Heroku CLI**: Follow Heroku’s instructions.
2. **Create Procfile**:
   - Add file `Procfile` with: `web: streamlit run app.py --server.port $PORT`
3. **Deploy**:
   - `heroku create`
   - `git push heroku main`
   - `heroku ps:scale web=1`
4. **Test**: Open the Heroku app URL and verify functionality.

## Troubleshooting
- **File Upload Issues**: Ensure the Excel file has the correct row structure and monthly columns.
- **Plot Errors**: Check `plots/` directory exists; verify `financial_log.txt` for matplotlib errors.
- **Proforma Issues**: Confirm 'Year' parsing and model R² scores in logs.

## Improvements
- Add `@st.cache_data` for faster data loading.
- Include sliders for adjusting proforma growth rates.
- Enable downloading proforma Excel via Streamlit button.



--------------------------------

# Deployment Guide for Financial Statement Analyzer

This guide provides instructions for setting up and deploying the Streamlit-based Financial Statement Analyzer application.

## 1. Installation (Local Setup)

To run the application locally, you need Python installed (preferably Python 3.8+). Follow these steps:

**a. Create a Virtual Environment (Recommended):**
Open your terminal or command prompt and navigate to the project directory.
```bash
python -m venv venv
```
Activate the virtual environment:
*   On Windows:
    ```bash
    venv\Scripts\activate
    ```
*   On macOS/Linux:
    ```bash
    source venv/bin/activate
    ```

**b. Install Dependencies:**
Create a `requirements.txt` file in your project's root directory with the following content:

```txt
# requirements.txt
pandas
openpyxl
numpy
scikit-learn
matplotlib
seaborn
streamlit
```

Then, install these dependencies using pip:
```bash
pip install -r requirements.txt
```
This command can also be run directly without a `requirements.txt` file:
```bash
pip install pandas openpyxl numpy scikit-learn matplotlib seaborn streamlit
```

## 2. Running Locally

Once the dependencies are installed, you can run the Streamlit application:

1.  Ensure your terminal is in the project's root directory (where `app.py` is located).
2.  Make sure your virtual environment is activated (if you created one).
3.  Run the following command:
    ```bash
    streamlit run app.py
    ```
This will start a local web server, and the application should open automatically in your default web browser. If not, the terminal will display a local URL (usually `http://localhost:8501`) that you can open.

## 3. Deployment Options

### a. Streamlit Community Cloud

Streamlit Community Cloud is the easiest way to deploy public Streamlit apps for free.

**Prerequisites:**
*   Your app code must be in a public GitHub repository.
*   Your repository must contain a `requirements.txt` file listing all dependencies.

**Steps:**
1.  **Push your code to GitHub:**
    *   Initialize a Git repository in your project folder if you haven't already (`git init`).
    *   Add your files (`git add app.py requirements.txt financial_log.txt .gitignore`). Create a `.gitignore` file and add `venv/`, `__pycache__/`, `*.pyc`, `plots/`, `*.csv`, `*.xlsx` (excluding template/example files if any) to it.
    *   Commit your changes (`git commit -m "Initial commit"`).
    *   Create a new public repository on GitHub.
    *   Link your local repository to the GitHub remote and push (`git remote add origin <your-repo-url>`, `git push -u origin main` or `master`).
2.  **Deploy from Streamlit Community Cloud:**
    *   Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with your GitHub account.
    *   Click "New app" or "Deploy an app".
    *   Choose your repository, branch, and the main Python file (e.g., `app.py`).
    *   Click "Deploy!".

Streamlit Cloud will automatically install dependencies from `requirements.txt` and run your app. Note that the `plots/` directory, `financial_log.txt`, and generated CSV/Excel files will be ephemeral on Streamlit Cloud (they will be reset on dyno restarts or new deployments). For persistent storage or more complex needs, consider other platforms or database solutions.

### b. Heroku

Heroku is another platform where you can deploy web applications.

**Prerequisites:**
*   Heroku CLI installed and logged in (`heroku login`).
*   Git installed.

**Steps:**
1.  **Prepare your app for Heroku:**
    *   Ensure you have `requirements.txt`.
    *   Create a `Procfile` (no extension) in your project's root directory with the following line:
        ```
        web: streamlit run app.py --server.headless true --server.enableCORS false --server.port $PORT
        ```
        *Note: The `--server.headless true --server.enableCORS false` flags are often recommended for Streamlit on Heroku.*
    *   Create a `setup.sh` file (optional, but can be useful for creating directories if needed, though `plots` dir is created by the app):
        ```bash
        # setup.sh
        mkdir -p logs
        mkdir -p plots 
        # (The app already creates 'plots', so this might be redundant unless you have other needs)
        ```
        If you use `setup.sh`, ensure it's executable (`chmod +x setup.sh`).
2.  **Initialize Git and commit your files** (if not already done for GitHub).
3.  **Create a Heroku app:**
    ```bash
    heroku create your-app-name
    ```
    (If you omit `your-app-name`, Heroku will generate one.)
4.  **Push your code to Heroku:**
    ```bash
    git push heroku main 
    ```
    (Or `master` if that's your default branch.)
5.  **Scale your dyno (if necessary):**
    Heroku's free tier usually provides one web dyno. If it's not started automatically:
    ```bash
    heroku ps:scale web=1
    ```
6.  **Open your app:**
    ```bash
    heroku open
    ```
    Similar to Streamlit Cloud, file system storage on Heroku is ephemeral.

## 4. Suggested Improvements

Here are some potential improvements for the application:

1.  **Caching DataFrames:**
    *   Use Streamlit's caching mechanisms (`@st.cache_data` for functions returning data like DataFrames) to improve performance, especially for repeated operations or when multiple users access the app. This can prevent re-reading and re-processing the Excel file on every interaction if the input file hasn't changed.
    *   Example:
        ```python
        @st.cache_data
        def load_and_process_sheet(excel_file_obj, sheet_name):
            # ... logic to read and return initial df_hierarchical ...
            return df_hierarchical

        @st.cache_data
        def perform_cleaning(_df_hierarchical, sheet_name): # Note: _df_hierarchical to indicate it's cached
            # ... logic for clean_and_transform_dataframe ...
            return cleaned_ts_df
        
        @st.cache_data
        def perform_proforma_analysis(_cleaned_ts_df, sheet_name, run_timestamp_str):
            # ... logic for generate_proforma_and_visualizations ...
            return proforma_df, plot_paths
        ```
    *   Care must be taken with mutable objects and how caching interacts with them. The `run_timestamp_str` might need careful handling if it's part of a cached function's input that should change per run.

2.  **Interactive Growth Assumptions:**
    *   Add `st.slider` or `st.number_input` widgets in the Streamlit sidebar or within each tab to allow users to adjust assumptions for the proforma forecast (e.g., apply a percentage growth rate to forecasted income/expenses instead of pure linear regression). This would require modifying the forecasting logic in `generate_proforma_and_visualizations`.

3.  **Download Proforma Excel:**
    *   The script now includes a basic `st.download_button` for the generated proforma Excel file. This is a good user experience feature.

4.  **Enhanced Error Alerts for Invalid Sheets:**
    *   While the app logs and shows `st.warning` for invalid sheets or processing errors, consider a more prominent summary of skipped sheets or critical errors at the top or bottom of the results page.
    *   For example, maintain a list of skipped sheets and reasons, then display this list.

5.  **Advanced Forecasting Models:**
    *   Linear regression is very basic. For more accurate financial forecasting, explore time series models like ARIMA, SARIMA, Exponential Smoothing, or machine learning regression models (e.g., Random Forest, Gradient Boosting) if sufficient data is available. This would significantly increase complexity.

6.  **Persistent Storage for Plots/Reports:**
    *   For deployments where the local file system is ephemeral (like Streamlit Cloud or Heroku's free tier), if you need to persist generated plots or reports, integrate with cloud storage services (e.g., AWS S3, Google Cloud Storage) or a database.

7.  **User Authentication:**
    *   If the application handles sensitive financial data and is deployed publicly, implement user authentication to restrict access.

8.  **Modular Code Structure:**
    *   For larger apps, consider breaking down `app.py` into multiple Python files (modules) for better organization (e.g., one for data processing, one for forecasting, one for Streamlit UI components).
```

This completes the prompt. The `app.py` script now includes the Streamlit UI for displaying results in tabs, saving outputs, and improved logging. The `deployment_guide.md` provides comprehensive instructions and suggestions. Remember to create the `plots` directory or ensure the script can create it. The `requirements.txt` file should also be created as described in the deployment guide.# filepath: deployment_guide.md
# Deployment Guide for Financial Statement Analyzer

This guide provides instructions for setting up and deploying the Streamlit-based Financial Statement Analyzer application.

## 1. Installation (Local Setup)

To run the application locally, you need Python installed (preferably Python 3.8+). Follow these steps:

**a. Create a Virtual Environment (Recommended):**
Open your terminal or command prompt and navigate to the project directory.
```bash
python -m venv venv
```
Activate the virtual environment:
*   On Windows:
    ```bash
    venv\Scripts\activate
    ```
*   On macOS/Linux:
    ```bash
    source venv/bin/activate
    ```

**b. Install Dependencies:**
Create a `requirements.txt` file in your project's root directory with the following content:

```txt
# requirements.txt
pandas
openpyxl
numpy
scikit-learn
matplotlib
seaborn
streamlit
```

Then, install these dependencies using pip:
```bash
pip install -r requirements.txt
```
This command can also be run directly without a `requirements.txt` file:
```bash
pip install pandas openpyxl numpy scikit-learn matplotlib seaborn streamlit
```

## 2. Running Locally

Once the dependencies are installed, you can run the Streamlit application:

1.  Ensure your terminal is in the project's root directory (where `app.py` is located).
2.  Make sure your virtual environment is activated (if you created one).
3.  Run the following command:
    ```bash
    streamlit run app.py
    ```
This will start a local web server, and the application should open automatically in your default web browser. If not, the terminal will display a local URL (usually `http://localhost:8501`) that you can open.

## 3. Deployment Options

### a. Streamlit Community Cloud

Streamlit Community Cloud is the easiest way to deploy public Streamlit apps for free.

**Prerequisites:**
*   Your app code must be in a public GitHub repository.
*   Your repository must contain a `requirements.txt` file listing all dependencies.

**Steps:**
1.  **Push your code to GitHub:**
    *   Initialize a Git repository in your project folder if you haven't already (`git init`).
    *   Add your files (`git add app.py requirements.txt financial_log.txt .gitignore`). Create a `.gitignore` file and add `venv/`, `__pycache__/`, `*.pyc`, `plots/`, `*.csv`, `*.xlsx` (excluding template/example files if any) to it.
    *   Commit your changes (`git commit -m "Initial commit"`).
    *   Create a new public repository on GitHub.
    *   Link your local repository to the GitHub remote and push (`git remote add origin <your-repo-url>`, `git push -u origin main` or `master`).
2.  **Deploy from Streamlit Community Cloud:**
    *   Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with your GitHub account.
    *   Click "New app" or "Deploy an app".
    *   Choose your repository, branch, and the main Python file (e.g., `app.py`).
    *   Click "Deploy!".

Streamlit Cloud will automatically install dependencies from `requirements.txt` and run your app. Note that the `plots/` directory, `financial_log.txt`, and generated CSV/Excel files will be ephemeral on Streamlit Cloud (they will be reset on dyno restarts or new deployments). For persistent storage or more complex needs, consider other platforms or database solutions.

### b. Heroku

Heroku is another platform where you can deploy web applications.

**Prerequisites:**
*   Heroku CLI installed and logged in (`heroku login`).
*   Git installed.

**Steps:**
1.  **Prepare your app for Heroku:**
    *   Ensure you have `requirements.txt`.
    *   Create a `Procfile` (no extension) in your project's root directory with the following line:
        ```
        web: streamlit run app.py --server.headless true --server.enableCORS false --server.port $PORT
        ```
        *Note: The `--server.headless true --server.enableCORS false` flags are often recommended for Streamlit on Heroku.*
    *   Create a `setup.sh` file (optional, but can be useful for creating directories if needed, though `plots` dir is created by the app):
        ```bash
        # setup.sh
        mkdir -p logs
        mkdir -p plots 
        # (The app already creates 'plots', so this might be redundant unless you have other needs)
        ```
        If you use `setup.sh`, ensure it's executable (`chmod +x setup.sh`).
2.  **Initialize Git and commit your files** (if not already done for GitHub).
3.  **Create a Heroku app:**
    ```bash
    heroku create your-app-name
    ```
    (If you omit `your-app-name`, Heroku will generate one.)
4.  **Push your code to Heroku:**
    ```bash
    git push heroku main 
    ```
    (Or `master` if that's your default branch.)
5.  **Scale your dyno (if necessary):**
    Heroku's free tier usually provides one web dyno. If it's not started automatically:
    ```bash
    heroku ps:scale web=1
    ```
6.  **Open your app:**
    ```bash
    heroku open
    ```
    Similar to Streamlit Cloud, file system storage on Heroku is ephemeral.

## 4. Suggested Improvements

Here are some potential improvements for the application:

1.  **Caching DataFrames:**
    *   Use Streamlit's caching mechanisms (`@st.cache_data` for functions returning data like DataFrames) to improve performance, especially for repeated operations or when multiple users access the app. This can prevent re-reading and re-processing the Excel file on every interaction if the input file hasn't changed.
    *   Example:
        ```python
        @st.cache_data
        def load_and_process_sheet(excel_file_obj, sheet_name):
            # ... logic to read and return initial df_hierarchical ...
            return df_hierarchical

        @st.cache_data
        def perform_cleaning(_df_hierarchical, sheet_name): # Note: _df_hierarchical to indicate it's cached
            # ... logic for clean_and_transform_dataframe ...
            return cleaned_ts_df
        
        @st.cache_data
        def perform_proforma_analysis(_cleaned_ts_df, sheet_name, run_timestamp_str):
            # ... logic for generate_proforma_and_visualizations ...
            return proforma_df, plot_paths
        ```
    *   Care must be taken with mutable objects and how caching interacts with them. The `run_timestamp_str` might need careful handling if it's part of a cached function's input that should change per run.

2.  **Interactive Growth Assumptions:**
    *   Add `st.slider` or `st.number_input` widgets in the Streamlit sidebar or within each tab to allow users to adjust assumptions for the proforma forecast (e.g., apply a percentage growth rate to forecasted income/expenses instead of pure linear regression). This would require modifying the forecasting logic in `generate_proforma_and_visualizations`.

3.  **Download Proforma Excel:**
    *   The script now includes a basic `st.download_button` for the generated proforma Excel file. This is a good user experience feature.

4.  **Enhanced Error Alerts for Invalid Sheets:**
    *   While the app logs and shows `st.warning` for invalid sheets or processing errors, consider a more prominent summary of skipped sheets or critical errors at the top or bottom of the results page.
    *   For example, maintain a list of skipped sheets and reasons, then display this list.

5.  **Advanced Forecasting Models:**
    *   Linear regression is very basic. For more accurate financial forecasting, explore time series models like ARIMA, SARIMA, Exponential Smoothing, or machine learning regression models (e.g., Random Forest, Gradient Boosting) if sufficient data is available. This would significantly increase complexity.

6.  **Persistent Storage for Plots/Reports:**
    *   For deployments where the local file system is ephemeral (like Streamlit Cloud or Heroku's free tier), if you need to persist generated plots or reports, integrate with cloud storage services (e.g., AWS S3, Google Cloud Storage) or a database.

7.  **User Authentication:**
    *   If the application handles sensitive financial data and is deployed publicly, implement user authentication to restrict access.

8.  **Modular Code Structure:**
    *   For larger apps, consider breaking down `app.py` into multiple Python files (modules) for better organization (e.g., one for data processing, one for forecasting, one for Streamlit UI components).
```

This completes the prompt. The `app.py` script now includes the Streamlit UI for displaying results in tabs, saving outputs, and improved logging. The `deployment_guide.md` provides comprehensive instructions and suggestions. Remember to create the `plots` directory or ensure the script can create it. The `requirements.txt` file should also be created as described in the deployment guide.