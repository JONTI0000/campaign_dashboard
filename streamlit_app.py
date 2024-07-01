import streamlit as st
import pandas as pd
import numpy as np
from streamlit_extras.metric_cards import style_metric_cards
import datetime
import matplotlib.pyplot as plt
import re
import plotly.express as px

def data_prep(df:pd.DataFrame):
    #converting to lower and removing empty spaces
    df["Name"] = df["Name"].str.lower().str.strip()
    df["Business Address"] = df["Business Address"].str.lower().str.strip()  

    df['Current Step'] = pd.to_numeric(df['Current Step'], errors='coerce')


    # Calculate time difference
    df['Acquired date'] = pd.to_datetime(df['Acquired date'])
    df['Sent Date-step 01'] = pd.to_datetime(df['Sent Date-step 01'],errors='coerce')
    df['Sent Date-step 02'] = pd.to_datetime(df['Sent Date-step 02'],errors='coerce')
    df['Sent Date-step 03'] = pd.to_datetime(df['Sent Date-step 03'],errors='coerce')
    df['Sent Date-step 04'] = pd.to_datetime(df['Sent Date-step 04'],errors='coerce')
    df['Sent Time-step-01'] = pd.to_datetime(df['Sent Time-step-01'], format='%H:%M:%S',errors='coerce').dt.time
    df['Sent Time-step-02'] = pd.to_datetime(df['Sent Time-step-02'], format='%H:%M:%S',errors='coerce').dt.time
    df['Sent Time-step-03'] = pd.to_datetime(df['Sent Time-step-03'], format='%H:%M:%S',errors='coerce').dt.time
    df['Sent Time-step-04'] = pd.to_datetime(df['Sent Time-step-04'], format='%H:%M:%S',errors='coerce').dt.time
    return df

def overall_analysis(df:pd.DataFrame):
    summary = {}
    reply_status_counts = df['Reply status'].value_counts()
    summary["qualified count"] = reply_status_counts.get('Yes', 0) + reply_status_counts.get('Filled form', 0)
    summary["bounced count"] = reply_status_counts.get('Bounced', 0)
    summary["Autoreply count"] = reply_status_counts.get('Auto Reply', 0)
    summary["emails delivered count"]= df['Current Step'].sum() - summary['bounced count']
    return summary

def batch_analysis(df:pd.DataFrame):
    leads = df.groupby('Batch No').size().reset_index(name='Leads in a Batch')
    bounced = df[df['Reply status'] == "Bounced"].groupby('Batch No').size().reset_index(name='Emails Bounced')
    email_sent = df.groupby('Batch No')['Current Step'].sum().reset_index(name='Emails Sent')
    auto_reply = df[df['Reply status'] == "Auto Reply"].groupby('Batch No').size().reset_index(name='Emails Auto reply')
    qualified  = df[(df['Reply status'] == "Yes") | (df['Reply status'] == 'Filled form')].groupby('Batch No').size().reset_index(name='Qualified Leads')

    result = pd.merge(leads, bounced, on='Batch No', how='left')
    result = pd.merge(email_sent, result, on='Batch No', how='left')
    result = pd.merge(auto_reply, result, on='Batch No', how='left')
    result = pd.merge(qualified, result, on='Batch No', how='left')

        # Rename columns
    result = result.rename(columns={'Index': 'Batch No', 'Leads in a Batch': 'Leads', 'Emails Auto reply': 'Auto replies'})

    # Calculate bounced rate
    result['Bounced rate (%)'] = (result['Emails Bounced'] / result['Leads']) * 100

    # Calculate emails delivered
    result['Emails delivered'] = result['Emails Sent'] - result['Emails Bounced']

    # Calculate qualified emails
    result['Qualified emails'] = result['Qualified Leads']

    # Calculate qualified rate
    result['Qualified rate (%)'] = (result['Qualified emails'] / result['Emails delivered']) * 100

    # Reorganize the DataFrame and set 'Batch No' as the index
    result = result[['Batch No', 'Leads', 'Emails Sent', 'Emails Bounced', 'Bounced rate (%)', 'Emails delivered', 'Auto replies', 'Qualified emails', 'Qualified rate (%)']]
    result.set_index('Batch No', inplace=True)

    return result

def step_analysis(df):
    step=df[(df["Reply status"] == "Yes") | (df["Reply status"] == "Filled form")]
    qualified = step.groupby("Current Step").size().reset_index(name="qualified")
    sent_df = {
            "Current Step":[1.0,2.0,3.0,4.0],
            "count":[df["Sent Date-step 01"].count(),
                        df["Sent Date-step 02"].count(),
                        df["Sent Date-step 03"].count(),
                        df["Sent Date-step 04"].count()]
            }

    sent = pd.DataFrame(sent_df)
    result= pd.merge(qualified,sent,on="Current Step",how="left")
    result.rename(columns={"Current Step":"Step","count":"Emails Sent"},inplace=True)
    result['qualify rate(%)'] = (result['qualified'] / result['Emails Sent']) * 100
    new_order = ['Step', 'Emails Sent', 'qualified', 'qualify rate(%)']
    result = result[new_order]
    result.set_index("Step",inplace=True)

    return result

def timeseries_analysis(df):
    quali = df[(df["Reply status"] == "Yes") | (df["Reply status"] == "Filled form")]
    def get_sent_date(row):
        current_step = row['Current Step']
        if pd.isna(current_step):
            return np.nan
        else:
            current_step = int(current_step)
            if current_step == 1:
                return row['Sent Date-step 01']
            elif current_step == 2:
                return row['Sent Date-step 02']
            elif current_step == 3:
                return row['Sent Date-step 03']
            elif current_step == 4:
                return row['Sent Date-step 04']
            else:
                return np.nan
    def get_sent_time(row):
        current_step = row['Current Step']
        if pd.isna(current_step):
            return np.nan
        else:
            current_step = int(current_step)
            if current_step == 1:
                return row['Sent Time-step-01']
            elif current_step == 2:
                return row['Sent Time-step-02']
            elif current_step == 3:
                return row['Sent Time-step-03']
            elif current_step == 4:
                return row['Sent Time-step-04']
            else:
                return np.nan

    quali['Sent Date'] = quali.apply(get_sent_date, axis=1)
    quali['Sent Time'] = quali.apply(get_sent_time, axis=1)
    quali =  quali[~quali["Batch No"].isin(["Not from Cadence"])]
    quali = quali[["Area",'Name','Batch No','Current Step','Reply status','Acquired date','Sent Date', 'Sent Time']]
    quali["Days taken to sign up"] = (quali["Acquired date"] - quali["Sent Date"]).dt.days
    quali["sent day"] = quali["Sent Date"].dt.day_name()
    quali["acquired day"] = quali["Acquired date"].dt.day_name()
    return quali

google_sheets_link = st.text_input('Google Sheet Link')
if google_sheets_link == "":
    st.write("Enter Google Sheets link")
else:
    link = re.sub(r'/edit\?usp=(sharing|drivesdk)$', '/export?format=xlsx', google_sheets_link)
    try:
        df = pd.read_excel(link,"Email Tracker")
        if df is None:
            st.text("Data is not loaded")
        else:
            df = data_prep(df)
            data_load_state = st.text('Loaded Data Successfully')

            overall_analysis = overall_analysis(df)
            batch_view = batch_analysis(df)
            st.title("Overall Analysis")
            #overall view
            col1,col2,col3,col4 = st.columns(4,gap="small")
            col1.metric(label="Qualified Leads", value=overall_analysis["qualified count"],delta=round(overall_analysis["qualified count"]/batch_view["Leads"].sum()*100,2))
            col2.metric(label="Bounced", value=overall_analysis["bounced count"],delta=round(overall_analysis["bounced count"]/batch_view["Leads"].sum()*100,2))
            col3.metric(label="Auto Replies", value=overall_analysis["Autoreply count"],delta=round(overall_analysis["Autoreply count"]/batch_view["Leads"].sum()*100,2))
            col4.metric(label="Emails Delivered", value=overall_analysis["emails delivered count"])
            style_metric_cards(background_color="#0100",border_radius_px=10,box_shadow=True)

            #batch view
            st.title("Batch Analysis")

            st.dataframe(batch_view,use_container_width=True)

            # Create a bar chart
            # Calculate percentages for each category
            batch_view['Bounced (%)'] = (batch_view['Emails Bounced'] / batch_view['Leads']) * 100
            batch_view['Auto Reply (%)'] = (batch_view['Auto replies'] / batch_view['Leads']) * 100
            batch_view['Qualified (%)'] = (batch_view['Qualified emails'] / batch_view['Leads']) * 100

            # Create a bar chart
            fig = px.bar(batch_view, x=batch_view.index, y=['Bounced (%)', 'Auto Reply (%)', 'Qualified (%)'],
                         title='Breakdown of each batch',
                         labels={'value': 'Percentage', 'variable': 'Category', 'index': 'Batch No'},
                         barmode='group')

            # Show the plot
            st.plotly_chart(fig)

            #step analysis
            st.title("Step Analysis")

            step_view = step_analysis(df)
            # Pie chart using plotly express
            fig = px.pie(step_view, values='qualified', names=step_view.index, title='Qualified Leads Distribution Among Steps', 
                         labels={'Step': 'Step', 'qualified': 'Qualified Leads'})

            # Create the bar chart
            #fig = px.bar(step_view, x=step_view.index, y='qualified', text='qualify rate(%)', title='Qualified leads by each step')
            # Update layout and add labels
            #fig.update_traces(texttemplate='%{text:.2f}', textposition='outside',width=0.4)
            # Show the figure
            st.plotly_chart(fig)
            st.dataframe(step_view,use_container_width=True)

            st.title("Time Series Analysis")
            quali = timeseries_analysis(df)
            
            #Main line chart
            days_taken = quali["Days taken to sign up"].value_counts().reset_index().sort_values("Days taken to sign up")
            fig = px.line(days_taken, x='Days taken to sign up', y='count', title='Days Taken to Sign Up')
            fig.update_layout(xaxis_title='Days', yaxis_title='Count', xaxis=dict(showgrid=True), yaxis=dict(showgrid=True))
            st.plotly_chart(fig)


            sent_day = quali["sent day"].value_counts().reset_index()
            fig = px.bar(sent_day, x='sent day', y='count', color='sent day', title='Days on which emails to qualified leads were sent')
            fig.update_layout(xaxis_title='Sent Day', yaxis_title='Count', showlegend=False)
            fig.update_traces(width=0.4)
            st.plotly_chart(fig)

            acquired_day = quali["acquired day"].value_counts().reset_index()
            fig = px.bar(acquired_day, x='acquired day', y='count', color='acquired day', title='Days on which leads were acquired')
            fig.update_layout(xaxis_title='Acquired Day', yaxis_title='Count', showlegend=False)
            fig.update_traces(width=0.6)
            st.plotly_chart(fig)

            quali['Sent Time'] = pd.to_datetime(quali['Sent Time'],format='%H:%M:%S')
            quali["sent hour"] = quali["Sent Time"].dt.hour
            sent_times = quali["sent hour"].value_counts().reset_index()
            fig = px.bar(sent_times.sort_values("sent hour"), x='sent hour', y='count', title='Times on which emails were sent(24 hour) to qualified leads')
            # Update layout and bar width
            fig.update_layout(xaxis_title='Sent Hour', yaxis_title='Count')
            fig.update_traces(width=0.4)  # Adjust width to make bars thinner
            st.plotly_chart(fig)


            

    except FileNotFoundError:
       st.text("File Does Not Exist")