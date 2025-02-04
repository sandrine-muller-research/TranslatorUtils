
import requests
# import json
import time
import csv
import os
import sys
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

## Translator UTILS
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
        # json_url = urlopen(url_response)
        # trapi_results_json = json.loads(json_url.read())
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


