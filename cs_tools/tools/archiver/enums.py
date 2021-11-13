import enum


class ContentType(enum.Enum):
    answer = 'answer'
    pinboard = 'pinboard'
    all = 'all'


class UserActions(enum.Enum):
    view_answer = 'ANSWER_VIEW'
    edit_answer = 'ANSWER_SAVED'
    view_pinboard = 'PINBOARD_VIEW'
    view_old_embed_pinboard = 'PINBOARD_EMBED_VIEW'
    view_embed_pinboard = 'PINBOARD_TSPUBLIC_RUNTIME_FILTER'
    view_embed_filtered_pinboard_view = 'PINBOARD_TSPUBLIC_NO_RUNTIME_FILTER'

    @classmethod
    def strigified(cls, sep: str=' ', context: str=None) -> str:
        mapper = {
            'answer': [
                'ANSWER_VIEW',
                'ANSWER_SAVED'
            ],
            'pinboard': [
                'PINBOARD_VIEW',
                'PINBOARD_EMBED_VIEW',
                'PINBOARD_TSPUBLIC_RUNTIME_FILTER',
                'PINBOARD_TSPUBLIC_NO_RUNTIME_FILTER'
            ]
        }
        allowed = mapper.get(context, [_.value for _ in cls])
        return sep.join([_.value for _ in cls if _.value in allowed])
