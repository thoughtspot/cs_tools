from typing import Any, Dict, List
import logging
import enum
import csv
import io

from pydantic.dataclasses import dataclass
from sqlalchemy_redshift import dialect
import sqlalchemy as sa
import s3fs


log = logging.getLogger(__name__)


class AuthType(enum.Enum):
    local = 'local'
    okta = 'okta'


@dataclass
class Redshift:
    """
    Interact with an AWS Redshift database.
    """
    username: str
    password: str
    database: str
    aws_access_key: str  # for S3 data load
    aws_secret_key: str  # for S3 data load
    aws_endpoint: str  # FMT: <clusterid>.xxxxxx.<aws-region>.redshift.amazonaws.com
    port: int = 5439
    auth_type: AuthType = AuthType.local
    # okta_account_name: str = None
    # okta_app_id: str = None
    truncate_on_connect: bool = True

    # DATABASE ATTRIBUTES
    __is_database__ = True
    metadata = None

    def __post_init_post_parse__(self):
        if self.auth_type == AuthType.local:
            connect_args = {}
            url = sa.engine.URL.create(
                drivername='redshift+redshift_connector',
                host=self.aws_endpoint,
                port=self.port,
                database=self.database,
                username=self.username,
                password=self.password
            )

        elif self.auth_type == AuthType.okta:
            # aws_cluster_id, _, aws_region, *_ = self.aws_endpoint.split('.')
            # connect_args = {
            #     'credentials_provider': 'OktaCredentialsProvider',
            #     'idp_host': '<prefix>.okta.com',
            #     'app_id': '<appid>',
            #     'app_name': 'amazon_aws_redshift',
            #     'cluster_identifier': aws_cluster_id,
            #     'region': aws_region,
            #     'ssl_insecure': False,
            #     **connect_args
            # }
            # url = sa.engine.URL.create(
            #     drivername='redshift+redshift_connector',
            #     database=self.database,
            #     username=self.username,
            #     password=self.password
            # )
            raise NotImplementedError(
                'our implementation is best-effort, but lacks testing.. see the source '
                'code for ideas on how to implement MFA to Okta.'
            )

        self.engine = sa.create_engine(url, connect_args=connect_args)
        self.cnxn = self.engine.connect()

        # decorators must be declared here, SQLAlchemy doesn't care about instances
        sa.event.listen(sa.schema.MetaData, 'after_create', self.capture_metadata)

    def capture_metadata(self, metadata, cnxn, **kw):
        self.metadata = metadata

        if self.truncate_on_connect:
            with self.cnxn.begin():
                for table in reversed(self.metadata.sorted_tables):
                    self.cnxn.execute(table.delete().where(True))

    def __repr__(self):
        return f"<Database ({self.name}) sync: conn_string='{self.engine.url}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return 'redshift'

    def load(self, table: str) -> List[Dict[str, Any]]:
        t = self.metadata.tables[table]

        with self.cnxn.begin():
            r = self.cnxn.execute(t.select())

        return [dict(_) for _ in r]

    def dump(self, table: str, *, data: List[Dict[str, Any]]) -> None:
        t = self.metadata.tables[table]

        # 1. Load file to S3
        fs = s3fs.S3FileSystem(key=self.aws_access_key, secret=self.aws_secret_key)
        fp = f's3://{self.s3_bucket_name}/ts_{table}.csv'

        with io.StringIO() as buf, fs.open(fp, 'w') as f:
            header = list(data[0].keys())
            writer = csv.DictWriter(buf, fieldnames=header, dialect='excel', delimiter='|')
            writer.writeheader()
            writer.writerows(data)

            f.write(buf.getvalue())

        # 2. Perform a COPY operation
        q = dialect.CopyCommand(t, data_location=fp, ignore_header=0)

        with self.cnxn.begin():
            self.cnxn.execute(q)  # .execution_options(autocommit=True)
