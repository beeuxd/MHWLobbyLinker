def welcome_screen():
  print("""
  ###################
  #     welcome     #
  #                 #
  ####################
  """)

def ready_to_play():
    print("Are you ready to play")
    return str(input())
    
    
def river_screen():
    print("""
  You need to cross a river.
  Do you...
  [1] use old bridge
  [2] swim across
  [3] build a boat
    """)
  
def read_option():
   print("what option would you like to choose")
   return int(input())