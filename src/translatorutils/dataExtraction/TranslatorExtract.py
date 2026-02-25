import requests
# import json
import time
import csv
import os
import sys
import concurrent.futures
import sqlite3
# import numpy as np
# import argparse


sys.path.append(os.path.join(os.getcwd()))


## UTILS:
def list_to_str(l):
    if l == None:
        l = '[]'
    elif isinstance(l,list)&(len(l)>1):
        l = '{' + ','.join(l) + '}'
    elif isinstance(l,list)&(len(l)==1):
        l = l[0]
        
    return l

def save_list_txt_file(L,filepath_string):
    with open(filepath_string, mode='w', encoding='utf-8', newline='') as fp:
        writer = csv.writer(fp, delimiter='\t')
        # for item in L:
        writer.writerows(L)

def add_table_from_dict(data_dict, table_name, conn=None):
    """
    Adds a new `table_name` table on the form of a dictionnary `data_dict` where each key is a column name and each value is a row to an SQLite database.

    Parameters:
        data_dict (dict): a dictionnary containing data
        conn (sqlite3.Connection): SQLite database connection.
        table_name (str): Name of the table to create or modify.

    Returns:
        None
    """  
    if not data_dict or not isinstance(data_dict, dict):
        raise ValueError("data_dict must be a non-empty dictionary.")

    # Use existing connection or create a new in-memory database
    if conn is None:
        conn = sqlite3.connect(":memory:")

    cursor = conn.cursor()

    # Check if the table already exists
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        # Dynamically create the table with columns based on the dictionary keys
        columns_def = ", ".join([f'"{key}" TEXT' for key in data_dict.keys()])  # Use TEXT for simplicity
        create_table_query = f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns_def});"
        cursor.execute(create_table_query)

    # Insert the row into the table
    columns = ", ".join(data_dict.keys())
    placeholders = ", ".join(["?" for _ in data_dict])
    insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});"
    cursor.execute(insert_query, tuple(data_dict.values()))

    # Commit changes and return connection
    conn.commit()
    
    return conn

def search_and_return_values(conn, my_input_list, T, attribute_to_search, attribute_to_return, T_prime=None):
    """
    Searches for strings in my_input_list in attribute_to_search of table T and retrieves the corresponding
    values for attribute_to_return. If attribute_to_return is not in T, it uses table T' (if provided).
    
    Parameters:
        conn (sqlite3.Connection): SQLite database connection object.
        my_input_list (list of str): List of strings to search.
        T (str): Name of the table to search.
        attribute_to_search (str): Column name in table T to search for values.
        attribute_to_return (str): Column name whose values are to be returned.
        T_prime (str, optional): Name of another table where attribute_to_return exists if not in T.
    
    Returns:
        list: A list of values for attribute_to_return corresponding to my_input_list, in the same order.
    """
    # Create placeholders for parameterized query
    placeholders = ', '.join(['?'] * len(my_input_list))  # e.g., "?, ?, ?"
    
    # Determine which table contains attribute_to_return
    if T_prime is None:
        # If no T_prime is provided, assume attribute_to_return is in T
        query = f"""
        SELECT {attribute_to_search}, {attribute_to_return}
        FROM {T}
        WHERE {attribute_to_search} IN ({placeholders});
        """
    else:
        # If T_prime is provided, join T and T_prime on common attributes
        query = f"""
        SELECT {T}.{attribute_to_search}, {T_prime}.{attribute_to_return}
        FROM {T}
        INNER JOIN {T_prime}
        ON {T}.{attribute_to_search} = {T_prime}.{attribute_to_search}
        WHERE {T}.{attribute_to_search} IN ({placeholders});
        """
    
    # Execute the query with parameterized inputs
    cursor = conn.cursor()
    cursor.execute(query, my_input_list)
    
    # Fetch results as a dictionary mapping attribute_to_search -> attribute_to_return
    rows = cursor.fetchall()
    if len(rows) != 0:
        result_map = {row[0]: row[1] for row in rows}
        out = [result_map.get(value, None) for value in my_input_list]
    else:
        out = None

    return out

def search_and_get_table(conn, my_input_list, T, attribute_to_search):
    """
    Searches for strings in my_input_list in attribute_to_search of table T and retrieves the corresponding
    values for attribute_to_return. If attribute_to_return is not in T, it uses table T' (if provided).
    
    Parameters:
        conn (sqlite3.Connection): SQLite database connection object.
        my_input_list (list of str): List of strings to search.
        T (str): Name of the table to search.
        attribute_to_search (str): Column name in table T to search for values.
        attribute_to_return (str): Column name whose values are to be returned.
        T_prime (str, optional): Name of another table where attribute_to_return exists if not in T.
    
    Returns:
        list: A list of values for attribute_to_return corresponding to my_input_list, in the same order.
    """
    # Create placeholders for parameterized query
    placeholders = ', '.join(['?'] * len(my_input_list))  # e.g., "?, ?, ?"
    
    # Determine which table contains attribute_to_return
    query = f"""
    SELECT *
    FROM {T}
    WHERE {attribute_to_search} IN ({placeholders});
    """
    
    # Execute the query with parameterized inputs
    cursor = conn.cursor()
    cursor.execute(query, my_input_list)
    
    # Fetch results as a dictionary mapping attribute_to_search -> attribute_to_return
    rows = cursor.fetchall()
    if len(rows) != 0:
        out = [list(r) for r in rows]
    else:
        out = None

    return out
        
def update_or_add_column_with_list(conn, table_name, my_column,default_value, my_column_condition=None, my_list=None, my_value=None):
    """
    Adds a column to the specified SQLite table (if it doesn't exist) and updates its values
    based on whether `my_column_condition` matches any value in `my_list`.

    Parameters:
        conn (sqlite3.Connection): SQLite database connection.
        table_name (str): Name of the table to modify.
        my_column (str): Name of the column to add or update.
        my_column_condition (str): Name of the column used for conditional checks.
        my_list (list): List of values to match in `my_column_condition`.
        my_value (float): Value to set in the new column for rows matching the condition.

    Returns:
        None
    """
    cursor = conn.cursor()

    # Step 1: Check if the column already exists
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [info[1] for info in cursor.fetchall()]  # Column names are in the second field

    # Step 2: Add the column if it doesn't exist
    if my_column not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {my_column} REAL DEFAULT {default_value}")

    if (my_column_condition is not None) and (my_list is not None) and (my_value is not None):
        # Step 3: Update rows where `my_column_condition` matches values in `my_list`
        if my_list:  # Ensure my_list is not empty
            placeholders = ', '.join('?' for _ in my_list)  # Create placeholders for SQL query
            sql_query = f"""
                UPDATE {table_name}
                SET {my_column} = ?
                WHERE {my_column_condition} IN ({placeholders})
            """
            cursor.execute(sql_query, [my_value] + my_list)

    # Commit changes to the database
    conn.commit()
    
    return conn

def save_KG_in_db(conn,db_file):
    # Open a connection to a file-based database
    file_db = sqlite3.connect(db_file)

    # Backup the in-memory database to the file-based database
    conn.backup(file_db)

    print(f"In-memory database backed up to {db_file}")

    # # Close both connections
    # file_db.close()
    
    return conn

def KG_table_to_SQLite(KG_table, table_name, conn=None):
    if not KG_table or len(KG_table) < 2:
        raise ValueError("Data must contain at least one header row and one data row.")

    # Extract headers and rows
    headers = KG_table[0]
    rows = KG_table[1:]

    # Use the provided connection or create a new in-memory database
    if conn is None:
        conn = sqlite3.connect(":memory:")

    cursor = conn.cursor()

    # Check if the table already exists
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        # Create table dynamically based on headers
        columns = ", ".join([f'"{header}" TEXT' for header in headers])  # All columns as TEXT for simplicity
        create_table_query = f"CREATE TABLE {table_name} ({columns});"
        cursor.execute(create_table_query)

    # Insert rows into the table, avoiding duplicates
    for row in rows:
        # Extract `node_ID` or `(node_1_ID, node_2_ID)` from the row
        node_1_ID = row[headers.index("node_1_ID")] if "node_1_ID" in headers else None
        node_2_ID = row[headers.index("node_2_ID")] if "node_2_ID" in headers else None

        # Check for duplicates in the database
        if node_1_ID and node_2_ID:
            query = f"SELECT 1 FROM {table_name} WHERE node_1_ID=? AND node_2_ID=?;"
            cursor.execute(query, (node_1_ID, node_2_ID))
            duplicate_exists = cursor.fetchone() is not None
        elif "node_ID" in headers:
            node_ID = row[headers.index("node_ID")]
            query = f"SELECT 1 FROM {table_name} WHERE node_ID=?;"
            cursor.execute(query, (node_ID,))
            duplicate_exists = cursor.fetchone() is not None
        else:
            duplicate_exists = False

        # Insert only if no duplicate exists
        if not duplicate_exists:
            placeholders = ", ".join(["?" for _ in headers])
            insert_query = f"INSERT INTO {table_name} VALUES ({placeholders});"
            cursor.execute(insert_query, row)

    # Commit changes (not strictly necessary for in-memory databases)
    conn.commit()

    return conn

## Translator UTILS - ARAS
def get_info_cond(info_list,info_to_get,condition_key,condition_value, separator = ';'):
    # function that from a list info_list, get the value for key info_to_get string if string condition_key is condition_value else return an empty string
    # if multiple values, the values are joined with separator
    out = ''
    for item in info_list:
        if info_to_get in item and condition_key in item:
            if item[condition_key] == condition_value:
                if info_to_get in item:
                    if isinstance(item[info_to_get], list):
                        item[info_to_get] = separator.join(item[info_to_get])
                    out = out + separator + item[info_to_get]
    if len(out)>0:
        out = out[1:]
        
    return out
    
def get_primary_source(source_info):
    # function that returns the primary source of an edge (tested for ARAX only)
    primary_source = get_info_cond(source_info,'resource_id','resource_role','primary_knowledge_source')
        
    return primary_source

def get_synonym(node_info):
    if 'attributes' in node_info:
        attributes = node_info['attributes']
        synonym = get_info_cond(attributes,'value','attribute_type_id','biolink:synonym')
        synonym = synonym.split(';')
        synonym = synonym[0]
    else:
        synonym = ''
        
    return synonym
    
def get_category(node_info,separator=';'):
    if 'categories' in node_info:
        category = node_info['categories']
        if isinstance(category,list):
           category = separator.join(category)
    else:
        category = ''
    return category
              
def get_KG_from_aras_message(q):
    KG_out = []
    KG_table = [["id","ARA","subject","subject name","subject_category","object","object name","object_category","predicate","primary_source"]] 
    
    for aras_response in q:
        if aras_response != None:
            if 'resource_id' in aras_response:
                ARA = aras_response['resource_id']
            else:
                ARA = ''
            if 'status' in aras_response:
                if isinstance(aras_response['status'],str):
                    if aras_response['status'].lower() == 'success':
                        if 'message' in aras_response:
                            message = aras_response['message']
                            if 'knowledge_graph' in message:
                                KG = message['knowledge_graph']
                                if 'nodes' in KG:
                                    nodes = KG['nodes']
                                if 'edges' in KG:
                                    edges_ids = list(KG['edges'].keys())
                                    if len(edges_ids)>0:
                                        for edges_id in edges_ids: 
                                            edge = KG['edges'][edges_id]
                                            if 'sources' in edge:
                                                source_info = edge['sources']
                                                primary_source = get_primary_source(source_info)
                                            if 'subject' in edge:
                                                subject = edge['subject']
                                                if subject in nodes:
                                                    subject_info = nodes[subject]
                                                    subject_category = get_category(subject_info)
                                                    subject_name = get_synonym(subject_info)
                                            else:
                                                subject = ''
                                            if 'object' in edge:
                                                object_ = edge['object']
                                                if object_ in nodes:
                                                    object_info = nodes[object_]
                                                    object_category = get_category(object_info)
                                                    object_name = get_synonym(object_info)
                                            else:
                                                object_ = ''
                                            if 'predicate' in edge:
                                                predicate = edge['predicate']
                                            else:
                                                predicate = ''

                                            edge_info = [edges_id,ARA,subject,subject_name,subject_category,object_,object_name,object_category,predicate,primary_source]
                                            KG_table.append(edge_info)
                                            
                                            edge_info = {'data':{'id': edges_id,'source': subject, 'target': object_, 'label': predicate, 'primary_source': primary_source, 'ARA':ARA}}
                                            subject_info = {'data':{'id':subject,'label':subject_name,'category':subject_category}}
                                            object_info = {'data':{'id':object_,'label':object_name,'category':object_category}}
                                            KG_out.append(subject_info)
                                            KG_out.append(object_info)
                                            KG_out.append(edge_info)
    return KG_out,KG_table
    
    
def make_post_request(url_ara, json_message, headers = {'Content-Type': 'application/json','accept': 'application/json'}):
    response = requests.post(url_ara, json=json_message, headers=headers)
    print(url_ara)
    print("POST response status code:", response.status_code)
    return response

def ars_submit(trapi_query_message, instance='prod', timeout=2000, interval=5):
    if instance == 'test':
        url_ars = 'https://ars.test.transltr.io/ars/api/submit/'
    elif instance == 'ci':
        url_ars = 'https://ars.ci.transltr.io/ars/api/submit/'
    elif instance == 'dev':
        url_ars = 'https://ars-dev.transltr.io/ars/api/submit/'
    else:
        url_ars = 'https://ars-prod.transltr.io/ars/api/submit/'
    
    response = make_post_request(url_ars, trapi_query_message, headers={'Content-Type': 'application/json','accept': 'application/json'})
    PK = response.json()['pk']
    
    print('response PK:')
    print(PK)
    
    # Initial status check with safety
    ars_response = get_trapi_message(PK, instance)
    if ars_response is None:
        print("Initial status check failed")
        return None
        
    # Handle already-complete case (Colab race condition fix)
    if ars_response['fields']['code'] in [200, 400]:
        print(f"Job already {ars_response['fields']['status']} (code: {ars_response['fields']['code']})")
        return ars_response
    
    start_time = time.time()
    while (time.time() - start_time < timeout):
        print(ars_response['fields']['status'])
        
        # Safe polling with null check
        try:
            if ars_response is None:
                ars_response = get_trapi_message(PK, instance)
                time.sleep(interval)
                continue
                
            code = ars_response['fields']['code']
            if code in [200, 400]:
                print(f"Final status: {ars_response['fields']['status']}")
                return ars_response
                
        except (KeyError, TypeError) as e:
            print(f"Polling error: {e}, retrying...")
            ars_response = None  # Force retry
        
        time.sleep(interval)
        ars_response = get_trapi_message(PK, instance)
    
    # Timeout case
    print(f"Timeout after {timeout}s, final status: {ars_response['fields']['status'] if ars_response else 'Unknown'}")
    return ars_response

def aras_submit(json_message,instance = 'prod'):
    
    if instance == 'dev':
        # set up dev environments:
        url_aragorn = 'https://aragorn.renci.org/aragorn/query?answer_coalesce_type=all'
        url_arax = 'https://arax.ncats.io/beta/api/arax/v1.4/query'
        url_biothings = 'https://api.bte.ncats.io/v1/query'
        url_improving = 'https://ia.healthdatascience.cloud/api/v1.5/query'
        url_medikanren = 'https://medikanren-trapi.ci.transltr.io/query'
    
    url_all_aras = [url_aragorn,url_arax,url_biothings,url_improving,url_medikanren]
    
    
    aras_responses = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit all requests to the executor
        future_to_url = {executor.submit(make_post_request, url, json_message): url for url in url_all_aras}
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                response = future.result()
                aras_responses.append(response.json())
            except Exception as exc:
                print(f'{url} generated an exception: {exc}')

    return aras_responses

## Translator UTILS -ARS
def KG_reorder_input(input_node_id,KG):
    
    KG_reorder = [[row[0],row[4],row[5],row[6],row[1],row[2],row[3],row[7]] if row[1]!=input_node_id else row for row in KG[1:]]
    
    return KG_reorder

def get_trapi_message_from_backedup():
    try:
        url_response = 'https://ars.ci.transltr.io/ars/api/messages/'
        json_url = requests.get(url_response)#urlopen(url_response)
        trapi_results_json = json_url.json()
        # trapi_results_json = json.loads(json_url.read())
    except:
        trapi_results_json = None
        
    return trapi_results_json

def get_query_info(q):
    subject = q['query_graph']['edges']["t_edge"]["subject"]
    predicate = q['query_graph']['edges']["t_edge"]["predicates"]
    object = q['query_graph']['edges']["t_edge"]["object"]    
    subject_type = q['query_graph']['nodes'][subject]['categories']
    object_type = q['query_graph']['nodes'][object]['categories']
    Q = q['query_graph']['nodes']
    
    if isinstance(predicate,list):
        predicate_type = list_to_str([p for p in predicate])
    
    if isinstance(subject,list):
        subject_val = list_to_str([Q[s]['ids'] if 'ids' in s.keys() else None for s in subject])
    else:
        if 'ids' in Q[subject].keys():
            subject_val = list_to_str(Q[subject]['ids'])
        else:
            subject_val = list_to_str(None)
    
    if isinstance(object,list):
        object_val = list_to_str([Q[o]['ids']  if 'ids' in o.keys() else None for o in object])
    else:
        if 'ids' in Q[object].keys():
            object_val = list_to_str(Q[object]['ids'])  
        else:
            object_val = list_to_str(None)
    
    return (list_to_str(subject_type) + ' ' + subject_val + ' ' + list_to_str(predicate_type) + ' ' + list_to_str(object_type) + ' ' + object_val, list_to_str(subject_type), list_to_str(predicate), list_to_str(object_type))

def get_info(q,ii):
    
    results_out = []
    
    results = q['results']
    KG = q['knowledge_graph']['edges']
    edge_ids = []
    
    if len(results)!=0:
        for idx,res in enumerate(results):
            if 'normalized_score' in res.keys():
                score = res['normalized_score']
            else:
                score = None
            
            if 'edge_bindings' in res.keys():
                edges_bindings = res['edge_bindings']
                
                for k,v in edges_bindings.items():
                    if v != None:
                        edge_ids = edge_ids + [(idx+ii,score,ids['id']) for ids in v]          
            else:
                edges_bindings = None
                edge_ids = None

        if edge_ids != None:
            for e in edge_ids:
                if e[2] in KG.keys():
                    K = KG[e[2]]
                    subject = K['subject']
                    object = K['object']
                    predicate = K['predicate']
                    attributes = K['attributes']
                    
                    attributes_num = 0
                    for att in attributes:
                        if att["attribute_type_id"]== "biolink:publications":
                            publications = att["value"]
                            if publications != None:
                                for pub in publications:
                                    results_out.append((e[0],e[1],e[2],subject,predicate,object,pub))
                        else:
                            attributes_num = attributes_num + 1
                    if len(attributes)==attributes_num:
                        results_out.append((e[0],e[1],e[2],subject,predicate,object,None))
                else:
                    results_out.append((e[0],e[1],e[2],None,None,None,None))
        else:
                    results_out.append((None,None,None,None,None,None,None))
                    
    else:
        results_out.append((None,None,None,None,None,None,None)) 
    
    return results_out

def get_trapi_message(PK,instance = 'prod'):
    
    if instance == 'test':
        url_response = 'https://ars.test.transltr.io/ars/api/messages/' + PK 
    elif instance == 'ci':
        url_response = 'https://ars.ci.transltr.io/ars/api/messages/' + PK 
    elif instance == 'dev':
        url_response = 'https://ars-dev.transltr.io/ars/api/messages/' + PK
    else:
        url_response = 'https://ars-prod.transltr.io/ars/api/messages/' + PK
    
    try:
        json_url = requests.get(url_response)
        trapi_results_json = json_url.json()
    except:
        trapi_results_json = None
        
    return trapi_results_json


def create_result_table(PK,instance = 'prod'):
    results_out = []
    # edge_num = 0
    print("Get TRAPI query message...")
    start = time.process_time()
    ARS_message = get_trapi_message(PK,instance)
    print(["Get TRAPI query message...Done. ",str(time.process_time() - start)])

    
    print("Get results message...")
    start = time.process_time()
    results_message = get_trapi_message(ARS_message["fields"]["merged_version"])
    print(["Get results message...Done. ",str(time.process_time() - start)])
    
    print("Format results...")
    start = time.process_time()
    results_list  = results_message["fields"]["data"]["message"]["results"]
    #auxiliary_graph_dict  = results_message["fields"]["data"]["message"]["auxiliary_graphs"]
    results_out = []
    for i_r, r in enumerate(results_list): # ['result_id','result_normalized_score','aux_graph_id','subject','predicate','object','publication'] 
        
        if 'node_bindings' in r:
            
            if "analyses" in r:
                for a in r["analyses"]:
                    if "support_graphs" not in a:
                        a["support_graphs"] = ""
                    if 'normalized_score' not in a:
                        a['normalized_score'] = 0
                    if 'score' not in a:
                        a['score'] = 0
                    if 'sugeno' not in a:
                        a['sugeno'] = 0
                    if 'weighted_mean' not in a:
                        a['weighted_mean'] = 0
                    if 'resource_id' not in a:
                        a['resource_id'] = ""
                    if 'rank' not in a:
                        a['rank'] = 0
                                     
                results_out.append([i_r,a['resource_id'],a['normalized_score'],a['weighted_mean'],a['sugeno'],a['rank'],a["support_graphs"],r['node_bindings']['n00'][0]['id'],r['node_bindings']['n01'][0]['id']]) # IMPROVEMENT ADD SUPPORT GRAPH DATA / ONLY TRUE FOR SINGLE INPUT DATA

def find_reverse_predicates(current_node_id_list,next_nodes_table):
    # find reverse predicates
    node_ID_reverse_predicates_list = []
    headers = next_nodes_table[0]
    next_nodes_table2 = []
    next_nodes_table2.append(headers)
    L = len(headers)
    for current_node_id in current_node_id_list:
        for n in next_nodes_table[1:]:
            if n[1]!= current_node_id:
                # search if edge is bidirectional, and ignore if so
                is_bidirectional = [True if nn[1] == current_node_id else False for nn in next_nodes_table][0]
                if not is_bidirectional:
                    node_ID_reverse_predicates_list = node_ID_reverse_predicates_list + [n[1]]
                    next_nodes_table2.append([n[0]]+n[4:7]+n[1:4]+list(n[7:]))
                else:
                    next_nodes_table2.append([n[0]]+n[4:7]+n[1:4]+list(n[7:]))
            else:
                next_nodes_table2.append(n)
                
    return next_nodes_table2,node_ID_reverse_predicates_list
 
def get_KG_out_table(PK,instance = 'prod'):
    ARS_message = None
    KG_out = [["id", "subject","subject name","subject_category","object","object name","object_category","predicate"]] 
    print("Get TRAPI query message...")
    start = time.process_time()
    while ARS_message is None:
        ARS_message = get_trapi_message(PK, instance)
        print(["Get TRAPI query message...Done. ",str(time.process_time() - start)])

    if ARS_message["fields"]["merged_version"] is not None:
        print("Get results message...")
        start = time.process_time()
        results_message = get_trapi_message(ARS_message["fields"]["merged_version"], instance)
        print(["Get results message...Done. ",str(time.process_time() - start)])
        
        print("Format KG...")  
        start = time.process_time()
        KG = results_message["fields"]["data"]["message"]["knowledge_graph"]["edges"]
        nodes_info = results_message["fields"]["data"]["message"]["knowledge_graph"]["nodes"]
        cpt = 0
        for edge in KG:
            if 'subject' in KG[edge]:
                subject = KG[edge]["subject"]
                if subject in nodes_info:
                    if "categories" in nodes_info[subject]:
                        subject_category = nodes_info[subject]["categories"][0]
                    else:
                        subject_category = ""
                        
                    if "name" in nodes_info[subject]:
                        subject_name = nodes_info[subject]["name"]
                    else:
                        subject_name = ""        
            else:
                subject = ""
                
            if 'object' in KG[edge]:
                object = KG[edge]["object"]
                if object in nodes_info:
                    if "categories" in nodes_info[object]:
                        object_category = nodes_info[object]["categories"][0]
                    else:
                        object_category = ""
                        
                    if "name" in nodes_info[object]:
                        object_name = nodes_info[object]["name"]
                    else:
                        object_name = ""
            else:
                object = ""
            if 'predicate' in KG[edge]:
                predicate = KG[edge]["predicate"]
            else:
                predicate = ""
            
            cpt += 1
            KG_out.append([cpt,subject,subject_name,subject_category,object,object_name,object_category,predicate])
                
        
        print(["Format KG...Done. ",str(time.process_time() - start)])            
    else:
        KG_out = None
        
    return KG_out

def get_KG_in_table(PK,instance = 'prod'):
    ARS_message = None
    KG_out = [["id", "subject","subject name","subject_category","object","object name","object_category","predicate"]] 
    print("Get TRAPI query message...")
    start = time.process_time()
    while ARS_message is None:
        ARS_message = get_trapi_message(PK, instance)
        print(["Get TRAPI query message...Done. ",str(time.process_time() - start)])

    if ARS_message["fields"]["merged_version"] is not None:
        print("Get results message...")
        start = time.process_time()
        results_message = get_trapi_message(ARS_message["fields"]["merged_version"], instance)
        print(["Get results message...Done. ",str(time.process_time() - start)])
        
        print("Format KG...")  
        start = time.process_time()
        KG = results_message["fields"]["data"]["message"]["knowledge_graph"]["edges"]
        nodes_info = results_message["fields"]["data"]["message"]["knowledge_graph"]["nodes"]
        cpt = 0
        for edge in KG:
            if 'subject' in KG[edge]:
                subject = KG[edge]["subject"]
                if subject in nodes_info:
                    if "categories" in nodes_info[subject]:
                        subject_category = nodes_info[subject]["categories"][0]
                    else:
                        subject_category = ""
                        
                    if "name" in nodes_info[subject]:
                        subject_name = nodes_info[subject]["name"]
                    else:
                        subject_name = ""        
            else:
                subject = ""
                
            if 'object' in KG[edge]:
                object = KG[edge]["object"]
                if object in nodes_info:
                    if "categories" in nodes_info[object]:
                        object_category = nodes_info[object]["categories"][0]
                    else:
                        object_category = ""
                        
                    if "name" in nodes_info[object]:
                        object_name = nodes_info[object]["name"]
                    else:
                        object_name = ""
            else:
                object = ""
            if 'predicate' in KG[edge]:
                predicate = KG[edge]["predicate"]
            else:
                predicate = ""
            
            cpt += 1
            KG_out.append([cpt,subject,subject_name,subject_category,object,object_name,object_category,predicate])
                
        
        print(["Format KG...Done. ",str(time.process_time() - start)])            
    else:
        KG_out = None
        
    return KG_out

def get_KG_table(PK, instance = 'prod', graph_selection = 'out'):  

    if graph_selection == 'out':
        KG_out = get_KG_out_table(PK, instance)
    else:
        KG_in = get_KG_in_table(PK, instance)
                                
    return KG_out


if __name__ == "__main__":
    message = {'message': {'query_graph': {'nodes': {'n0': {'ids': ['NCBI:100288687']},
    'n1': {'categories': ['biolink:ChemicalEntity']}},
   'edges': {'e0': {'subject': 'n0',
     'object': 'n1',
     'predicates': ['affects'],
     'knowledge_type': 'inferred'}}}}}
    
    print('testing ARAS submit...')
    response = ars_submit(message,instance='dev',timeout = 5000, interval = 5)
