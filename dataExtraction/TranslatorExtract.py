import requests
# import json
import time
import csv
import os
import sys
import concurrent.futures
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
    
    # primary_source = ''
    # for source in source_info:
    #     if 'resource_role' in source and 'resource_id' in source:
    #         if source['resource_role'] == 'primary_knowledge_source':
    #             primary_source = primary_source + ';' + source['resource_id']
    # if len(primary_source)>0:
    #     primary_source = primary_source[1:]
        
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
    # KG_out = [["id","ARA","subject","subject name","subject_category","object","object name","object_category","predicate","primary_source"]] 
    KG_out = []
    
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

                                            # edge_info = [edges_id,ARA,subject,subject_name,subject_category,object_,object_name,object_category,predicate,primary_source]
                                            
                                            edge_info = {'data':{'id': edges_id,'source': subject, 'target': object_, 'label': predicate, 'primary_source': primary_source, 'ARA':ARA}}
                                            subject_info = {'data':{'id':subject,'label':subject_name,'category':subject_category}}
                                            object_info = {'data':{'id':object_,'label':object_name,'category':object_category}}
                                            KG_out.append(subject_info)
                                            KG_out.append(object_info)
                                            KG_out.append(edge_info)
    return KG_out
    
    
def make_post_request(url_ara, json_message, headers = {'Content-Type': 'application/json','accept': 'application/json'}):
    response = requests.post(url_ara, json=json_message, headers=headers)
    print(url_ara)
    print("POST response status code:", response.status_code)
    return response

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
    
    KG_reorder = [[row[0],row[4],row[5],row[6],row[1],row[2],row[3],row[7]] if row[1]!=input_node_id and row[1]!='subject' else row for row in KG]
    
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
 
def get_KG_table(PK, instance = 'prod'):  
    KG_out = [["id", "subject","subject name","subject_category","object","object name","object_category","predicate"]] 
    print("Get TRAPI query message...")
    start = time.process_time()
    ARS_message = get_trapi_message(PK, instance)
    print(["Get TRAPI query message...Done. ",str(time.process_time() - start)])

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
            subject = None
            
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
            object = None
        if 'predicate' in KG[edge]:
            predicate = KG[edge]["predicate"]
        else:
            predicate = None
        
        cpt += 1
        KG_out.append([cpt,subject,subject_name,subject_category,object,object_name,object_category,predicate])
            
    
    print(["Format KG...Done. ",str(time.process_time() - start)])            
    
                                
    return KG_out


