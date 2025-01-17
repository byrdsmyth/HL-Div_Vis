"""
   Implementation of the different strategy summarization Algorithms we used.
   *random_state_selection() chooses random summaries.
   *highlights implements the HIGHLIGHTS algorithm.
   *highlights_div implements the HIGHLIGHTS-DIV algorithm.
"""

import numpy as np
import pandas as pd
import os
import re
from bisect import bisect
from bisect import insort_left
import image_utils
from scipy.spatial import distance
import coloredlogs, logging

def print_df(stats_df):
    print("DF: ")
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
        print(stats_df)

def random_state_selection(state_importance_df, budget, context_length, minimum_gap, seed = None):
    ''' generate random summary
    :param state_importance_df: dataframe with 2 columns: state and importance score of the state
    :param budget: allowed length of summary - note this includes only the important states, it doesn't count context
    around them
    :param context_length: how many states to show around the chosen important state (e.g., if context_lenght=10, we
    will show 10 states before and 10 states after the important state
    :param minimum_gap: how many states should we skip after showing the context for an important state. For example, if
    we chose state 200, and the context length is 10, we will show states 189-211. If minimum_gap=10, we will not
    consider states 212-222 and states 178-198 because they are too close
    :param seed: optional int to set a seed
    :return: a list with the indices of the randomly chosen states, and a list with all summary states (includes the context)
    '''
    shuffled_states = state_importance_df.sample(frac=1.0, random_state=seed, replace=True)
    summary_states = []
    for index, row in shuffled_states.iterrows():

        state_index = row['state']
        index_in_summary = bisect(summary_states, state_index)
        # print('state: ', state_index)
        # print('index in summary: ', index_in_summary)
        # print('summary: ', summary_states)
        state_before = None
        state_after = None
        if index_in_summary > 0:
            state_before = summary_states[index_in_summary-1]
        if index_in_summary < len(summary_states):
            state_after = summary_states[index_in_summary]
        if state_after is not None:
            if state_index+context_length+minimum_gap > state_after:
                continue
        if state_before is not None:
            if state_index-context_length-minimum_gap < state_before:
                continue
        insort_left(summary_states,state_index)
        if len(summary_states) == budget:
            break

    summary_states_with_context = []
    for state in summary_states:
        min_range = int(state - context_length)
        max_range = int(state + context_length)
        summary_states_with_context.extend((range(min_range,max_range)))
    ls = [type(item) for item in summary_states_with_context]
    print("Type of random list before being returned from highlights random state selection is:")
    print(ls)
    return summary_states, summary_states_with_context

def highlights(state_importance_df, budget, context_length, minimum_gap):
    ''' generate highlights summary
    :param state_importance_df: dataframe with 2 columns: state and importance score of the state
    :param budget: allowed length of summary - note this includes only the important states, it doesn't count context
    around them
    :param context_length: how many states to show around the chosen important state (e.g., if context_lenght=10, we
    will show 10 states before and 10 states after the important state
    :param minimum_gap: how many states should we skip after showing the context for an important state. For example, if
    we chose state 200, and the context length is 10, we will show states 189-211. If minimum_gap=10, we will not
    consider states 212-222 and states 178-198 because they are too close
    :return: a list with the indices of the important states, and a list with all summary states (includes the context)
    '''
    logger = logging.getLogger()
    coloredlogs.install(level='DEBUG', fmt='%(asctime)s,%(msecs)03d %(filename)s[%(process)d] %(levelname)s %(message)s')
    
    logger.setLevel(logging.DEBUG)
        
    sorted_df = state_importance_df.sort_values(['importance'], ascending=False)
    summary_states = []
    for index, row in sorted_df.iterrows():

        state_index = row['state']
        index_in_summary = bisect(summary_states, state_index)
        # print('state: ', state_index)
        # print('index in summary: ', index_in_summary)
        # print('summary: ', summary_states)
        state_before = None
        state_after = None
        if index_in_summary > 0:
            state_before = summary_states[index_in_summary-1]
        if index_in_summary < len(summary_states):
            state_after = summary_states[index_in_summary]
        if state_after is not None:
            if state_index+context_length+minimum_gap > state_after:
                continue
        if state_before is not None:
            if state_index-context_length-minimum_gap < state_before:
                continue
        insort_left(summary_states,state_index)
        if len(summary_states) == budget:
            break

    summary_states_with_context = []
    for state in summary_states:
        summary_states_with_context.extend((range(state-context_length,state+context_length)))
    return summary_states, summary_states_with_context


# Assumes Euclidean Distance Metric, Goes through summary state list, calculates distance between features of the new state and each state in summary list already, and returns whether or not the two are too similar. The features are also known as the second to last layer of the network, which act similar to a feature vector for the DQN-network.
# So the summary states are ones where there is a drastice difference between q-values of the possible actions, and where the network's second to last layer has the most diversity.
def find_similar_state_in_summary(state_importance_df, summary_states, new_state, distance_metric, distance_threshold=None):
    logger = logging.getLogger()
    coloredlogs.install(level='DEBUG', fmt='%(asctime)s,%(msecs)03d %(filename)s[%(process)d] %(levelname)s %(message)s')
    
    logger.setLevel(logging.DEBUG)
    
    most_similar_state = None
    minimal_distance = 10000000
    for state in summary_states:
        state_features = state_importance_df.loc[state_importance_df['state'] == state].iloc[0].features
#        w.observe(state_features = state_features)
        distance = distance_metric(state_features, new_state)
#        w.observe(distance = distance)
        if distance < minimal_distance:
            minimal_distance = distance
            most_similar_state = state
    if distance_threshold is None:
        return most_similar_state, minimal_distance
    elif minimal_distance < distance_threshold:
        return most_similar_state, minimal_distance
    return None


def highlights_div(args, state_importance_df, budget, context_length, minimum_gap, distance_metric=distance.euclidean, percentile_threshold=3, subset_threshold = 10):
    ''' generate highlights-div  summary
    :param state_importance_df: dataframe with 2 columns: state and importance score of the state
    :param budget: allowed length of summary - note this includes only the important states, it doesn't count context
    around them
    :param context_length: how many states to show around the chosen important state (e.g., if context_lenght=10, we
    will show 10 states before and 10 states after the important state
    :param minimum_gap: how many states should we skip after showing the context for an important state. For example, if
    we chose state 200, and the context length is 10, we will show states 189-211. If minimum_gap=10, we will not
    consider states 212-222 and states 178-198 because they are too close
    :param distance_metric: metric to use for comparing states (function)
    :param percentile_threshold: what minimal distance to allow between states in summary
    :param subset_threshold: number of random states to be used as basis for the div-threshold
    :return: a list with the indices of the important states, and a list with all summary states (includes the context)
    '''
    
    print("Trajectories: ")
    print(budget)
    print("context: ")
    print(context_length)
    print("Min gap: ")
    print(minimum_gap)
    
    logger = logging.getLogger()
    coloredlogs.install(level='DEBUG', fmt='%(asctime)s,%(msecs)03d %(filename)s[%(process)d] %(levelname)s %(message)s')
    
    logger.setLevel(logging.DEBUG)
    
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
        if (args.verbose):
            logger.info("state_features_importance_df")
            logger.info(state_importance_df)
            logger.info("In highlights DIV")
#    state_importance_df.index.name = 'state'
#    with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
#        print(state_importance_df)
    min_state = state_importance_df['state'].values.min()
    max_state = state_importance_df['state'].values.max()

    state_features = state_importance_df['features'].values
    # changed replace from True to False Dec. 4
    state_features = np.random.choice(state_features, size=subset_threshold, replace=False)
    distances = []
    for i in range(len(state_features-1)):
        for j in range(i+1,len(state_features)):
            distance = distance_metric(state_features[i],state_features[j])
            distances.append(distance)
    distances = np.array(distances)
    threshold = np.percentile(distances,percentile_threshold)
    if (args.verbose):
        print('threshold:',threshold)
        logger.info("About to call state_importance Sort_values")
    
    # Sorts by importance, then goes down the df
    # for each row, it finds where the state would fall in the summary list
    # Checks if the new state has enough distance between the state before and after
    # Checks if a state in the summary is already similar
    # If not, puts into list
    sorted_df = state_importance_df.sort_values(['importance'], ascending=False)
    summary_states = []
    summary_states_with_context = []
    num_chosen_states = 0
    for index, row in sorted_df.iterrows():
        if (args.verbose):
            logger.info("Iterating through df of sorted state features")
        state_index = row['state']
        index_in_summary = bisect(summary_states, state_index)
        if (args.verbose):
             print('state: ', state_index)
             print('index in summary: ', index_in_summary)
             print('summary: ', summary_states)
        state_before = None
        state_after = None
        if index_in_summary > 0:
            state_before = summary_states[index_in_summary-1]
        if index_in_summary < len(summary_states):
            state_after = summary_states[index_in_summary]
        if state_after is not None:
            if state_index+context_length+minimum_gap > state_after:
                continue
        if state_before is not None:
            if state_index-context_length-minimum_gap < state_before:
                continue

        # if num_chosen_states < budget:
        #     insort_left(summary_states,state_index)
        #     num_chosen_states += 1


        # compare to most similar state
        if (args.verbose):
            logger.info("About to call find_similar_state_in_summary")
        most_similar_state, min_distance = find_similar_state_in_summary(state_importance_df, summary_states_with_context, row['features'], distance_metric)
        if most_similar_state is None:
            insort_left(summary_states,state_index)
            num_chosen_states += 1
            if (args.verbose):
                print('summary_states:', summary_states)

        else:
            # similar_state_importance = state_importance_df.loc[state_importance_df['state'] == most_similar_state].iloc[0].importance
            # if row['importance'] > similar_state_importance:
            if min_distance > threshold:
                insort_left(summary_states,state_index)
                num_chosen_states += 1
                if (args.verbose):
                    print('summary_states:', summary_states)
                    print('took')
            else:
                if (args.verbose):
                    print(state_index)
                    print('skipped')

        #recalculate the context states
        summary_states_with_context = []
        for state in summary_states:
            if (args.verbose):
                logger.info("Iterating through summary states")
            # Removed coercion toInt on Dec 4
            left_index = max(int(state) - int(context_length),min_state)
            right_index = min(int(state) + int(context_length),max_state) +1
            summary_states_with_context.extend((range(left_index, right_index)))

        # Indented by one on Dec. 4
        if len(summary_states) == budget:
                logger.info("Hit budget limit")
                break
    if (args.verbose):
        logger.info("Returning from div highlights")
        logger.info("ONLY Summary states in highlights div are: ")
        logger.info(summary_states)
        logger.info("zsummary states in highlights div with context are: ")
        logger.info(summary_states_with_context)
        logger.info(list(summary_states_with_context))
    return summary_states, list(summary_states_with_context)


def compute_states_importance(args, states_q_values_df, compare_to='worst'):
    print("In compute state import and states are: ")
    print(states_q_values_df['state'])
    logger = logging.getLogger()
    coloredlogs.install(level='DEBUG', fmt='%(asctime)s,%(msecs)03d %(filename)s[%(process)d] %(levelname)s %(message)s')
    
    logger.setLevel(logging.DEBUG)
    
    if compare_to == 'worst':
        states_q_values_df['importance'] = states_q_values_df['q_values'].apply(lambda x: np.max(x)-np.min(x))
    elif compare_to == 'second':
        # Selects states based on the distribution of Q-values of different actions.
        # NP.partition = Creates a copy of the array with its elements rearranged in such a way that the value of the element in k-th position is in the position it would be in a sorted array. All elements smaller than the k-th element are moved before this element and all equal or greater are moved behind it. The ordering of the elements in the two partitions is undefined.
        # So it flattens the q-values, puts the last two in order, and selects the second-biggest number
        # So states with a obviously better Q-Value would have more importance (i think)
        states_q_values_df['importance'] = states_q_values_df['q_values'].apply(lambda x: np.max(x)-np.partition(x.flatten(), -2)[-2])
        
    importanceDF = pd.DataFrame()
    importanceDF['state'] = states_q_values_df.index
    importanceDF['importance'] = states_q_values_df['importance']
    filename = os.path.join(args.stream_folder, 'import.csv')
    importanceDF.to_csv(filename)
    
    return states_q_values_df

def read_q_value_files(path):
    ''' reading q values from files. Assume each state is a seperate text file with a list of q values
    :param path: path to the directory where the text files are stored
    :return: a pandas dataframe with two columns: state (index) and q_values (numpy array)
    '''
    logger = logging.getLogger()
    coloredlogs.install(level='DEBUG', fmt='%(asctime)s,%(msecs)03d %(filename)s[%(process)d] %(levelname)s %(message)s')
    
    logger.setLevel(logging.DEBUG)
    
    states = []
    q_values_list = []
    for filename in os.listdir(path):
        file_split = filename.split('_')
        print("file split is: " + str(file_split))
        state_index_temp = file_split[len(file_split)-1][:-4]
        state_index = re.search(r'\d+', state_index_temp).group()
        print("State index is: " + str(state_index))
        
        states.append(state_index)
        # print(filename)
        with open(path+'/'+filename, 'r') as q_val_file:
            q_vals = str.strip(q_val_file.read(),'[]')
            q_vals = np.fromstring(q_vals,dtype=float, sep=' ')
            q_values_list.append(q_vals)

    q_values_df = pd.DataFrame({'state':states, 'q_values':q_values_list})
    print("HighlightsSelect and q_values_df is: ")
    print_df(q_values_df)
    return q_values_df

def read_feature_files(path):
    ''' reading state features from files. Assume each state is a seperate text file with a feature vector
    :param path: path to the directory where the text files are stored
    :return: a pandas dataframe with two columns: state (index) and features (numpy array)
    '''
    logger = logging.getLogger()
    coloredlogs.install(level='DEBUG', fmt='%(asctime)s,%(msecs)03d %(filename)s[%(process)d] %(levelname)s %(message)s')
    
    logger.setLevel(logging.DEBUG)
    
    states = []
    feature_vector_list = []
    for filename in os.listdir(path):
        if not filename.endswith('.txt'):  # skip text files, use npy files
            continue
        file_split = filename.split('_')
        state_index = int(file_split[len(file_split)-1][:-4])
        states.append(state_index)
        # print(filename)
        with open(path+'/'+filename, 'r') as feature_file:
            features_text = str.strip(feature_file.read(),'[]')
            features_text = features_text.replace('\n', ' ')
            features_text = ' '.join(features_text.split())
            feature_vector = np.fromstring(features_text, dtype=float, sep=' ')
            feature_vector_list.append(feature_vector)

    state_features_df = pd.DataFrame({'state':states, 'features':feature_vector_list})
#    print("HighlightsSelect and state_features_df is: ")
#    print_df(state_features_df)
    return state_features_df

def read_input_files(path):
    '''reading state inputs from files. Assume each state is a seperate npy file with a array
    :param path: path to the directory where the npy files are stored
    :return: a pandas dataframe with two columns: state (index) and features (numpy array)
    The inputs are called features so one can use the df interchangeably with the one from read_feature_files.
    '''
    logger = logging.getLogger()
    coloredlogs.install(level='DEBUG', fmt='%(asctime)s,%(msecs)03d %(filename)s[%(process)d] %(levelname)s %(message)s')
    
    logger.setLevel(logging.DEBUG)
    
    states = []
    input_list = []
    for filename in os.listdir(path):
        if filename.endswith('.npy'):  # only use npy files
            file_split = filename.split('_')
            state_index = int(file_split[len(file_split) - 1][:-4])
            states.append(state_index)

            input = np.load(os.path.join(path,filename))
            input = input.flatten() #flatten arrays since we only need the distance between states
            input_list.append(input)

    state_input_df = pd.DataFrame({'state': states, 'features': input_list}) #we use features as name to make the div-code less bloated
#    print("HighlightsSelect and state_input_df is: ")
#    print_df(state_input_df)
    return state_input_df



if __name__ == '__main__':
    print("IN MAIN OF HIGHLIGHTS STATE SELECTION PYTHON FILE.....................................")
    #create wathcer object for MS tensorwatch
#    w = tw.Watcher()
    
    test = read_input_files('stream/state')


    # test_data = pd.DataFrame({'state':[1,2,3],'q_values':[[1,2,3],[1,1,1],[2,1,1]]})
    # # print(highlights(test_data,2))
    q_values_df = read_q_value_files('stream/q_values')
    states_q_values_df = compute_states_importance(args, q_values_df, compare_to='second')
    # # print(highlights(highlights,20,10,10))
    states_q_values_df.to_csv('states_importance_second.csv')
    # # a = np.array([1, 2, 3])
    # # b = np.array([4, 5, 6])
    # # print(distance.cosine(a,b))
    # # exit()
    states_q_values_df = pd.read_csv('states_importance_second.csv')
#    print("HighlightsSelect and states_q_values_df is: ")
#    print_df(states_q_values_df)
    
    features_df = read_feature_files('stream/features')
    features_df.to_csv('state_features.csv')
    features_df = pd.read_csv('state_features.csv')
#    print("HighlightsSelect and features_df is: ")
#    print_df(features_df)
    
    state_features_importance_df = pd.merge(states_q_values_df, features_df,on='state')
    state_features_importance_df = state_features_importance_df[['state','q_values','importance','features']]
    state_features_importance_df.to_csv('state_features_impoartance.csv')
    state_features_importance_df = pd.read_csv('state_features_impoartance.csv')
    state_features_importance_df['features'] = state_features_importance_df['features'].apply(lambda x:
                           np.fromstring(
                               x.replace('\n','')
                                .replace('[','')
                                .replace(']','')
                                .replace('  ',' '), sep=' '))
#    print("HighlightsSelect and state_features_importance_df is: ")
#    print_df(state_features_importance_df)
    
    summary_states, summary_states_with_context = highlights_div(args, state_features_importance_df, 15,10,10)
#    print('div:' ,summary_states)
    image_utils.generate_video('stream/argmax/','stream/','highlights_div_15_10_10.mp4', image_indices=summary_states_with_context)
    summary_states, summary_states_with_context = highlights(state_features_importance_df, 15,10,10)
#    print('reg', summary_states)
    image_utils.generate_video('stream/argmax/','stream/','highlights_reg_15_10_10.mp4', image_indices=summary_states_with_context)
    # exit()
    # summary_states, summary_states_with_context = highlights(states_q_values_df,20,10,10)

    # a = [1,4,6,10]
    # a.extend(range(20,30))
    # print(a)
    # print(bisect(a,7))

    # image_utils.generate_video('stream/argmax/','stream/','random_summary' +'_' +str(i) + '.mp4', image_indices=summary_states_with_context)
