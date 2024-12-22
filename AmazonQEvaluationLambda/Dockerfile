FROM public.ecr.aws/lambda/python:3.9

# Copy requirements.txt
COPY requirements.txt .

# Install the specified packages
RUN pip install -r requirements.txt

# Copy function code
COPY src/amazonq_evaluation_lambda .

CMD [ "handlers.q_evaluation_lambda_handler.lambda_handler" ]