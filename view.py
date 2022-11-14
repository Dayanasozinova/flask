from flask import Flask, jsonify, request
from flask.views import MethodView
from sqlalchemy import Integer, Column, String, DateTime, func, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.exc import IntegrityError
import atexit
import pydantic
from typing import Optional

app = Flask('view')

DSN = 'postgresql://app:1234@127.0.0.1:5431/ads'
engine = create_engine(DSN)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class HttpError(Exception):
    def __init__(self, status_code: int, message: str or dict or list):
        self.status_code = status_code
        self.message = message


@app.errorhandler(HttpError)
def http_error_handler(err: HttpError):
    response = jsonify({
        'status': 'error',
        'message': err.message
    })
    response.status_code = err.status_code
    return response


def on_exit():
    engine.dispose()


atexit.register(on_exit)


class Ads(Base):
    __tablename__ = 'ads'
    id = Column(Integer, primary_key=True)
    title = Column(String(50), nullable=False)
    description = Column(String(200), nullable=False)
    owner = Column(String, nullable=False)
    create_time = Column(DateTime, server_default=func.now())


Base.metadata.create_all(engine)


class CreateAdsSchema(pydantic.BaseModel):
    title: str
    description: str
    owner: str

    @pydantic.validator('title')
    def strong_title(cls, value: str):
        if len(value) <= 5:
            raise ValueError('title is too short')
        return value


class PatchAdsSchema(pydantic.BaseModel):
    title: Optional[str]
    description: Optional[str]
    owner: Optional[str]

    @pydantic.validator('title')
    def strong_title(cls, value: str):
        if len(value) <= 5:
            raise ValueError('title is too short')
        return value


def validate(Schema, data: dict):
    try:
        data_validated = Schema(**data).dict(exclude_none=True)
    except pydantic.ValidationError as er:
        raise HttpError(400, er.errors())
    return data_validated


def get_ads(ads_id: int, session: Session) -> Ads:
    ads = session.query(Ads).get(ads_id)
    if ads is None:
        raise HttpError(404, 'ads not found')
    return ads


class AdsView(MethodView):
    def get(self, ads_id: int):
        with Session() as session:
            ads = get_ads(ads_id, session)

        return jsonify({'title': ads.title, 'create_time': ads.create_time.isoformat()})

    def post(self):
        json_data_validate = validate(CreateAdsSchema, request.json)
        with Session() as session:
            new_ads = Ads(**json_data_validate)
            try:
                session.add(new_ads)
                session.commit()
            except IntegrityError:
                raise HttpError(400, 'ads already exist')
            return jsonify({'All': 'ok', 'id': new_ads.id})

    def patch(self, ads_id: int):
        json_data_validated = validate(PatchAdsSchema, request.json)
        with Session() as session:
            ads = get_ads(ads_id, session)
            for key, value in json_data_validated.items():
                setattr(ads, key, value)
            session.add(ads)
            session.commit()
        return jsonify({'stutus': 'ok'})

    def delete(self, ads_id):
        with Session as session:
            ads = get_ads(ads_id, session)
            session.delete(ads)
            session.commit()
        return jsonify({'stutus': 'ok'})


app.add_url_rule('/user/', methods=['POST'], view_func=AdsView.as_view('create_ads'))
app.add_url_rule('/user/<int:ads_id>', methods=['GET', 'PATCH', 'DELETE'], view_func=AdsView.as_view('get_ads'))
app.run()
