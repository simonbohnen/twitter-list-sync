import argparse
import twitter
import os


API1 = twitter.Api(consumer_key=os.environ.get('CONSUMER_KEY_1'),
                   consumer_secret=os.environ.get('CONSUMER_SECRET_1'),
                   access_token_key=os.environ.get('ACCESS_TOKEN_KEY_1'),
                   access_token_secret=os.environ.get('ACCESS_TOKEN_SECRET_1'),
                   sleep_on_rate_limit=False)

API2 = twitter.Api(consumer_key=os.environ.get('CONSUMER_KEY_2'),
                   consumer_secret=os.environ.get('CONSUMER_SECRET_2'),
                   access_token_key=os.environ.get('ACCESS_TOKEN_KEY_2'),
                   access_token_secret=os.environ.get('ACCESS_TOKEN_SECRET_2'),
                   sleep_on_rate_limit=False)

# This is the maximum number of list members that should be retrieved. The absolute maximum for the API is 5000.
max_list_members = 1000


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def remove_list_by_name(listslist, name):
    """
    Finds a list in a lists of lists by it's name, removes and returns it.
    :param listslist: A list of Twitter lists.
    :param name: The name of the list to be found.
    :return: The list with the name, if it was found. None otherwise.
    """
    for i in range(len(listslist)):
        if listslist[i].name == name:
            return listslist.pop(i)


def get_user_from_id(userlist, user_id):
    """
    Find a user in a list of users based on the user id.
    :param userlist: The list of users to be searched.
    :param user_id: The user id.
    :return: The user with the id if one was found, None otherwise.
    """
    for user in userlist:
        if user.id == user_id:
            return user


def sync_list_versions(api1, list1, name1, api2, list2, name2, verbose_output):
    """
    Syncs a list between two accounts.
    Each account will also have all the members of the list of the other account after returning.
    :param api1: The Twitter API object of the first account.
    :param list1: The list on the first account. Must be owned by the user that authenticated api1.
    :param name1: The name of the first account. Used for logging.
    :param api2: The Twitter API object of the second account.
    :param list2: The list on the second account. Must be owned by the user that authenticated api2.
    :param name2: The name of the second account. Used for logging.
    :param verbose_output: If true, output will be verbose
    :return: True if one of the list versions was changed, False otherwise.
    """

    # Get list members
    members1 = api1.GetListMembersPaged(list_id=list1.id, skip_status=True, count=max_list_members)[2]
    member2 = api2.GetListMembersPaged(list_id=list2.id, skip_status=True, count=max_list_members)[2]

    # Filter out protected members
    public_members1 = [u for u in members1 if not u.protected]
    public_members2 = [u for u in member2 if not u.protected]
    ignored_members_count1 = len(members1) - len(public_members1)
    ignored_members_count2 = len(member2) - len(public_members2)

    if (ignored_members_count1 != 0 or ignored_members_count2 != 0) and verbose_output:
        print("Ignoring protected accounts: %d on %s's account, %d on %s's"
              % (ignored_members_count1, name1, ignored_members_count2, name2))

    public_member_ids1 = [u.id for u in public_members1]
    public_member_ids2 = [u.id for u in public_members2]

    # Get members that are only in one of the lists
    newmember_ids1 = [uid for uid in public_member_ids2 if uid not in public_member_ids1]
    newmember_ids2 = [uid for uid in public_member_ids1 if uid not in public_member_ids2]

    if len(newmember_ids1) == 0 and len(newmember_ids2) == 0:
        if verbose_output:
            print("The list is in sync already.")
        return False

    if not verbose_output:
        print("List %s:" % list1.name)
    print("Adding members: %d to %s's account, %d to %s's"
          % (len(newmember_ids1), name1, len(newmember_ids2), name2))

    # Chunk them into hundreds
    newmemberschunked1 = chunks(newmember_ids1, 100)
    for c in newmemberschunked1:
        api1.CreateListsMember(list_id=list1.id, user_id=c)
    newmemberschunked2 = chunks(newmember_ids2, 100)
    for c in newmemberschunked2:
        api2.CreateListsMember(list_id=list2.id, user_id=c)

    if verbose_output:
        total1 = len(public_members1) + ignored_members_count1 + len(newmember_ids1)
        total2 = len(public_members2) + ignored_members_count2 + len(newmember_ids2)
        if total1 == total2:
            print("The list now has %d members on both accounts." % total1)
        else:
            print("The list now has %d members on %s's account and %d on %s's." % (total1, name1, total2, name2))

    return True


def ask_for_list_creation(listpairs, api, api_name, list1, store_new_list_first):
    create_list = input("List %s is missing on %s's account. Do you want to create it? [y/n] "
                        % (list1.name, api_name))
    if create_list == 'y':
        print("Creating list.")
        list2 = api.CreateList(list1.name, mode='private')
        if store_new_list_first:
            listpairs.append((list2, list1))
        else:
            listpairs.append((list1, list2))
    else:
        print("Skipping list.")


def sync_lists(api1, api2, excluded_list_names, verbose_output=False, send_summary_dm=False):
    """
    Syncs all lists between two users.
    Lists are identified by name.
    The list version of either account will be updated to the union of both versions.
    Deleting a member from a list is only possible if both remove the member from the list previous to the sync.
    Protected members are ignored. This can lead to different numbers of list members.
    If a list doesn't exist on an account, the user is asked if he wants to create it.
    :param api1: The api of the first user.
    :param api2: The api of the second user.
    :param excluded_list_names: A list of list names that should be excluded from syncing.
    :param verbose_output: If true, output will be verbose.
    :param send_summary_dm: If true, a summary direct message is sent from api1 to api2.
    """

    # Get lists from both accounts.
    lists1 = [list1 for list1 in api1.GetLists() if list1.name not in excluded_list_names]
    lists2 = [list2 for list2 in api2.GetLists() if list2.name not in excluded_list_names]

    # Get the names of the accounts used for logging.
    if len(lists1) == 0:
        name1 = "Account 1"
    else:
        name1 = lists1[0].user.screen_name

    if len(lists2) == 0:
        name2 = "Account 2"
        id2 = 0
        if send_summary_dm:
            send_summary_dm = False
            print("Could not get name of account 2. Won't send summary dm.")
    else:
        name2 = lists2[0].user.screen_name
        id2 = lists2[0].user.id

    if len(lists1) != len(lists2):
        print("Retrieved %d lists from %s's account, but %d from %s's" % (len(lists1), name1, len(lists2), name2))
    elif verbose_output:
        print('Retrieved %d lists on both accounts.' % len(lists1))

    if verbose_output:
        print("Making sure that the same lists exist on both accounts...")

    listpairs = []
    for list1 in lists1:
        # Get and remove list of second account based on name
        list2 = remove_list_by_name(lists2, list1.name)
        if list2 is None:
            ask_for_list_creation(listpairs, api2, name2, list1, False)
            continue

        if verbose_output:
            print("List %s is present on both accounts." % list1.name)
        listpairs.append((list1, list2))

    for list2 in lists2:
        # All the lists that remain in lists2 are not present on the first account.
        # That's why we ask whether we should create the list on the first account for each one of them.
        ask_for_list_creation(listpairs, api1, name1, list2, True)

    changed_any_list = False
    changed_list_names = []

    for l1, l2 in listpairs:
        if verbose_output:
            print("Syncing list %s" % l1.name)

        versions_were_different = sync_list_versions(api1, l1, name1, api2, l2, name2, verbose_output)

        if versions_were_different:
            changed_list_names.append(l1.name)

        changed_any_list = changed_any_list or versions_were_different

    if not changed_any_list:
        msg = "List sync complete. No changes made!"
        print(msg)
        if send_summary_dm:
            api1.PostDirectMessage(msg, user_id=id2)
    else:
        msg = "List sync complete. Made changes to lists %s." % ", ".join(changed_list_names)
        if verbose_output:
            print(msg)
        if send_summary_dm:
            api1.PostDirectMessage(msg, user_id=id2)


def main(verbose=False, send_summary_dm=True):
    excluded_lists_file = open("excluded_lists.txt", "r")
    excluded_names = excluded_lists_file.readlines()
    excluded_lists_file.close()

    if verbose:
        print("Excluded lists: %s" % ", ".join(excluded_names))

    sync_lists(API1, API2, excluded_names, verbose, send_summary_dm)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', help="have verbose output")
    parser.add_argument('--dm', action='store_true', help="send a summary dm between the two accounts after syncing")
    args = parser.parse_args()
    main(args.verbose, args.send_summary_dm)
