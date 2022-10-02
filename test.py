from sbs_utils.quests.quest import IF_EXP_REGEX, DICT_REGEX, STRING_REGEX, LIST_REGEX


print(r'((\-{2,})'+IF_EXP_REGEX+r'(\-{2,}))\n(?P<code>[\s\S]+?)\n(?P<loop>((\-{2,})|(\^{2,})))')

