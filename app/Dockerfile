FROM public.ecr.aws/lambda/python:3.10
COPY main.py ./
COPY requirements.txt ./
# install packages
RUN yum install -y gcc-c++ pkgconfig poppler-cpp-devel
RUN python3 -m pip install -r requirements.txt
# run lambda handler
CMD ["main.handler"]