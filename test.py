from sbs_utils.quests.quest import DICT_REGEX, STRING_REGEX, LIST_REGEX


print('(?P<scope>(shared|temp)\s+)?(?P<lhs>[\w\.\[\]]+)\s*=\s*(?P<exp>('+DICT_REGEX+'|'+STRING_REGEX+'|'+LIST_REGEX+'|.*))')

