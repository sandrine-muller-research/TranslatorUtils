

def pathfinder_message(ids_n0, ids_n2, categories, predicates):
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
                      "predicates": predicates[0],
                      "knowledge_type": "inferred"
                      },
                  "e1": {
                      "subject": "un",
                      "object": "n2",
                      "predicates": predicates[1],
                      "knowledge_type": "inferred"
                      },
                  "e2": {
                      "subject": "n0",
                      "object": "n2",
                      "predicates": predicates[2],
                      "knowledge_type": "inferred"
                      }
                  }
              }
          }
        }
    
    return message
