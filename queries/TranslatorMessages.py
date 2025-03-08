

def pathfinder_message(ids_n0, ids_n2, categories, predicates):
    if len(predicates) == 1:
        predicates [1] = predicates[0]
        predicates[2] = predicates[1]
        if len(predicates) ==2:
            print("not enough predicates")
    message = {
        "message" : {
          "query_graph": {
              "nodes": {
                  "n0": {
                      "ids": ids_n0
                      },
                  "un": {
                      "categories": categories
                      },
                  "n2": {
                      "ids": ids_n2
                      }
                  },
              "edges": {
                  "e0": {
                      "subject": "n0",
                      "object": "un",
                      "predicates": [predicates[0]],
                      "knowledge_type": "inferred"
                      },
                  "e1": {
                      "subject": "un",
                      "object": "n2",
                      "predicates": [predicates[1]],
                      "knowledge_type": "inferred"
                      },
                  "e2": {
                      "subject": "n0",
                      "object": "n2",
                      "predicates": [predicates[2]],
                      "knowledge_type": "inferred"
                      }
                  }
              }
          }
        }
    
    return message

def look_up_message(ids_current_node_list,predicates_list,next_node_categories_list = ["biolink:NamedThing"]):
    message = {
        "message" : {
          "query_graph": {
              "nodes": {
                  "n0": {
                      "ids": ids_current_node_list
                      },
                  "n1": {
                      "categories": next_node_categories_list
                      }
                  },
              "edges": {
                  "e0": {
                      "subject": "n0",
                      "object": "n1",
                      "predicates": predicates_list,
                      "knowledge_type": "lookup"
                      }
                  }
              }
          }
        }
    
    return message