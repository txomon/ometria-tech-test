About this repo
===============

This is a technical test for Ometria. I will paste the description below.

Original text
=============

Backend developer take home test
--------------------------------

You are tasked with designing a system for scheduling and running batch imports from 3rd party systems, converting the resulting data and sending on to the main internal data API for further processing and storage. (L1)

We have many individual client accounts, each of which contains many ‘contact’ records representing their email newsletter list. (L2)

An example of a contact record stored by Ometria is: (L3)
   {
     "id": "2343fgfdg",
     "firstname": "John",
     "lastname": "Smith",
     "email": "hello@world.com",
   }

The component you are to design will periodically connect to the 3rd party API and load records, convert it and forward it to the internal Ometria data API:: (L4)

 Internet   |                Ometria network

 3rd Party  <->  Importer system (tbd)     ->     Existing Ometria API


The principle will be that each account can have many ‘connections’ to different 3rd party lists. (L5)

Each connection pulls down from the 3rd party API at a certain frequency and sends them to the Ometria data API, ideally minimising the number of API operations required. (L6)

At the end of each ‘run’ the two systems should be in sync. (L7)

For the purposes of this example, the 3rd party API is that of Mailchimp, and each Ometria account for the purposes of this test may have 0 or more ‘connections’ to Mailchimp lists with associated access credentials. (L8)

See below for example API credentials that can be used for this test. (L9)

Each record type has a unique string ID (any string format, scoped within that account) which can be used to connect the record with the 3rd party system. (L10)

You can assume that the Ometria API is idempotent in that writing the same record (with the same ID) more than once will only result in one record being stored (with the value being that of the last write). (L11)

Accuracy and reliability of this system is of utmost importance. (L12)

The goal is to hold all the records in the 3rd party ‘source’ and keep them up to date, so that after each ‘batch run’ the records are the same. (L13)

If, for any reason, the system cannot update the connection, and falls behind more than a certain threshold, there should be some mechanism for alerting the technical team. (L14)

However, equally, it's likely there will be many thousands of connections, so preventing false errors is also important. (L15)

The worst possible result is that the importers silently fall out of sync, as at that point the statistics we report will be out of date. (L16)

Each importer needs to know how up to date it is so we never run reports on out of sync data. (L17)

The system should store its own state and configuration (e.g. for the connections). (L18)

Typically a batch import connection will run hourly. (L19)

This ideal system must be highly scalable. (L20)

Its likely that it will need to scale to many thousands of import jobs per hour. (L21)

To this end it must be designed to be scalable and also intelligently minimise the amount of information exchanged on each ‘sync’ to keep the stored records up to date with the 3rd party source. (L22)

Deliverables :
    1. Briefly discuss how you would design such a system. (L23)

    What software components will you use (databases? queues?)? (L24)

    Which components need to be developed internally by our team? (L25)

    Please discuss how would you guarantee the top level functional requirements above? (L26)

    Assume the system will be deployed on AWS using whatever AWS tools you would recommend. (L27)

    Briefly describe the AWS components required and how the logical components map onto them. (L28)

    2. Working code example. (L29)

    Please provide a runnable python project that can illustrate the main ‘sync’ algorithm, e.g. connect to a 3rd party system, load and map records, and push them to the Ometria data API. (L30)

    Send us a link to the code (github/bitbucket/etc) or zipped via email. (L31)

    A Dockerfile would be nice otherwise include instructions on how to run the script. (L32)


Required API resources.
Mailchimp:

API Key: XXXXXXXXXXXX
List ID: YYYYYYYYYYYY

Ometria data API:
Endpoint: http://ec2-34-242-147-110.eu-west-1.compute.amazonaws.com:8080/record
HTTP Method: POST
Payload is a JSON array of objects in the format above.
Header: Authorisation: <API Key, provided in email>

Deliverable One (L23)
=====================

First impression after reading the whole document is that it assumes there is previous knowledge on the data model, as the description of what is to be done includes definitions on the way. The first thing I would do would be to assert that the following data model is clear.

 * There are three players. 3rd parties, the TBD system, and the ometria API (L4)

 * There are the following entities:

   * Client account: This is a group of recipients, for example the subscribers to a newsletter. (L2)

     --- I suppose it represents a Ometia business client (L2) --- Correction, after reading all again, it looks like it is a mailing list, not a holder for many email lists as it seemed first. The part of "We have many individual client accounts" was misleading


   * Contact record: It's an email entry. (L3)

     ---A client has a list of Contacts. Each contact record is a communication channel, a mailing list---

     It has the following format: {id, firstname, lastname, email} (L3)


I cannot quite get what lines (L5, L6 and L7) refer to, as I don't see how a many to many relationships can be done. As there is no identifier of a 3rd party service in the body of a Contact Record I will just ignore those lines, as it shouldn't affect my output on Deliverables 1 or 2.

This can be modeled as an standard reliable batch job execution, similar to what I did in Jinn, I need to make sure that all the steps in the process are accounted and controlled, so that we can retry some of them if fail.

L13 seems to suggest we should not store all the records locally (The goal is to hold all the records in the 3rd party ‘source’) as opposed to (The goal is to hold locally all the records of the 3rd party 'source'). Because deletions are not mentioned anywhere else, it seems that we are encouraged to keep as little data of the 3rd party services locally.

However the importance given to this system and other statements (L10, L12, L14, L15, L16), I will proceed with a full blown solution that supports *Contact record* deletion, keeps track of latest imported data. This way, if L13 meant the opposite to what I understood, we can just rip off that part of the code. Better safe than regret.


Design
------

There are a few parts that need to exist:

  * Scheduler code: This will be the one in charge of generating import events.

  * Job tracking system: This should track what import tasks fail and which ones succeed.

  * Job execution code: This is the part that does a single step. Similar to what is asked by Deliverable 2. Additionally it should have mechanics on what to do when the Job tracking system detects jobs are not being completed.

Before giving a solution, I would need to check what degree of vendor dependency the company has with AWS. If the company has interest on having everything multicloud to avoid attacks like the ones to AWS in 2016 disrupting services, use of open source tools would be given, so as to deploy them over any infrastructure.

If the company wants a medium level of commitment, for example, they want to be able to deploy over AWS and GCP or Azure, then Code would be developed to use libraries that can be easily adapted to both systems, for example, ensuring libraries for services are platform compatible (kombu vs AWS SDK)

If the company doesn't mind that much vendor lock, which I would personally recommend because the business' core is not a cloud competing technological product (i.e. the product is not an scheduling system or an infrastructure service), then I would use as many AWS services as possible, so that there are less building blocks to maintain. There is no product value by reinventing the wheel in this case.

I am going to propose two designs, a fully opensource one, and a full AWS one. The medium one would be a mix between both. Because of the time that the technical test should last is two hours, I will leave infrastructure details out of it.

Without AWS
###########

Here the previous pieces of the system would be done fully on open source tools. Supposing we have a way to run programs ready (mesos, kubernetes, heroku, whatever), the implementation of the previous specificied building blocks would be as following a flow like this:


 Scheduler --(Batch import)-> Importer system --(n x (Account import))-> Importer system --(Diff data)-> Ometria API

 --(Importer system retry max reached)-> Importer system -(n x (Actions to be taken))-> Notification system -> Developers


Scheduler
~~~~~~~~~

I would code the job scheduler as an scheduling service tightly monitored, company wide level. This scheduler would be a company level cron service. This is because the maintenance of many different scheduling services doesn't scale good, as code is not reused and maintainability becomes an issue fast.

I would code it in py36 using APScheduler library to do the scheduling task. However, the cron wouldn't have domain knowledge of the rest of the system, and instead it would connect to a Queue system (Kafka, RabbitMQ) and schedule a "Batch import" message on the relevant queue/topic.

Job tracking
~~~~~~~~~~~~

A queue system with consumption tracking could be used for this scenario. The system would consist of the main flow, making sure that the company wide scheduler can trigger a batch import in the Importer System, which in return would multiply this task to n accounts, enqueueing a task for each account.

A sample batch import message would be `{"type": "importersystem.batch_import"}` and consumer would then generate n account specific messages like `{"type": "importersystem.account_import", "account": "1a8bb32cd"}`.

We would make sure that tasks are always executed, and if a task failed to execute, for example because a faulty node or some kind of temporal issue, retries are automatic, as the failed task would not be ACKed (or it would be NACKed), and it would return to the queue to be consumed by our software.

Some queue services have a feature called death letter queue, where messages that are retried fail to be ACKed a few times go to. This would allow to have a list of impossible tasks (Tasks that have been retried a sensible amount of times and still cannot be processed), and we could have code that depending of the amount of them could decide to either it as an exception, be aware that there are many exceptions, or for example, that a given task always fails.

This would allow the system to alert developers on some anomaly.

It is important to note just in case, that this design requires supplementary monitoring on the queues, as even if the system is well coded, and notifications could arise from it, if there is anything that doesn't allow things to go through (for example the code is not properly deployed), no notification would be possible to be triggered from this, and the only Infrastructure level sympthom that could allow to diagnose this would be the growth of the queue batch imports go to.

More specifically there should be no reason why a queue would grow without being consumed from. Therefore, an external software should monitor the queues, and alert developers that something is going wrong.

Job execution code
~~~~~~~~~~~~~~~~~~

This is the only piece of code that contains domain knowledge of the task in this exercise. It would have 3 main functions:

 * Transform a Batch import task into N account import tasks

 * Execute a given account import task, getting previous import data from the system storage, diff-ing previous data to new data, and submitting differences

 * Detect anomalies in the system by saving import failures, and decide when to trigger the notification system based on that


With AWS
########

The AWS design is based on the previous one, but using AWS tooling.

The list of the tools that could be used would be:

 * AWS Lambda: It's easy to deploy, and pricing is extremely appropriate for this usecase, as a pro it relieves the team from infrastructure maintenance tasks. It has the downside that memory usage and execution time is limited, but given the design, it shouldn't be a problem

 * AWS Batch: This is the traditional scheduling alternative. It has full blown job scheduling builtin, but having AWS Lambda nowadays, it's more appropriate for workloads where either the running time or memory usage limits in Lambda are exceeded. It is a wrapper around EC2.

 * AWS Kinesis: This is Kafka in AWS, it has the ability to trigger AWS Lambda when messages arrive, which makes it perfect for our usecase

 * AWS CloudWatch: A somewhat expensive service, it allows to monitor queue size and trigger notifications. It provides log aggregation too, which can be usefull to track task execution. We would need to be careful when using it, as pricing grows quite fast if used carelessly.

 * AWS DynamoDB: Because our *Importer System* needs to store the *Client Accounts* and *Contact Records* that we need to look for. I would go for DynamoDB as the storage, because it scales seamlessly, and the amount of maintenance on the system would be really low.


AWS Lambda has builtin scheduling, so we would just program the *Batch import* function in a hourly manner, which would in turn generate N import account events on Kinesis. AWS Lambda has also integration with Kinesis, therefore executing the Lambda functions to import specific accounts.


Final notes
###########

The outlined design has two main benefits, it's highly scalable, being able to process millions of accounts every hour if required, and the design is not oppinionated by the usecase. If we were to decide that we wanted to run all the accounts in cycling mini batches, instead of all of them at the same time in an hour, we would just need to change the scheduler to trigger job execution.

If an account were to be so big that it exceeded AWS Lambda execution times, we could always subdivide the task into several batches, similar to when we don't want to run all accounts at once. Another possibility would be to use AWS Lambda Step functions, where we define the whole workflow of importing one account, and make an iteration design where we would keep track on the current import status.

There is a chance that an account may take over an hour to execute, making not worth to schedule in an hourly manner, or if it still wants to have everything hourly synced, we would need to speedup the job, by parallelizing it even more.

As I explained on the beginning of the Deliverable one, we are encouraged to NOT keep *Contact Records* locally, however given the requirements of reliability, I decided to ignore that requirement, as I don't believe in 3rd parties being reliable. However, if we really didn't want to keep *Contact Records* locally, we would either need to drop support for deletions, or have the 3rd party provide deletions either through their API or push notification, or somehow else, so that we knew of specific records to delete.

Depending on the data retention we wanted to have, we could use S3 to store a zip file with the output of the 3rd parties, and use versioning + lifecycle management from S3 to progress old imports into glacier.


Deliverable Two (L29)
=====================

Because the whole test was supposed to take 2 hours, but there were too many caveats and somewhat confusing directions, I decided to take enough time to explain some of the possible directions I would take when creating the *Importer System*.

However, because of all the assumptions and options made for this tech test, and not to extend things more, I will be coding the "Job execution code", as defined in the Deliverable 2 (L30), using local storage instead of dynamodb/s3 as storage.

After a few minutes of work I realised that Mailchimp doesn't store name/surname, so I have no idea where those values should be coming from. I will leave them empty. Also, there is no API documentation for removals.

In order to run this, you can use pipenv to install all the deps (aiohttp + click), and you can supply the configuration through command line arguments or environment variables.

I have also created a docker compose for easy running, but this one only accepts environment variables (you can also supply stuff through arguments, but then you would need to edit the docker-compose file).

Quickstart, if you have pipenv installed, just do with python3.6, `pipenv install --ignore-pipfile`, and `pipenv run python sync.py ....` where you can use `pipenv run python sync.py --help` to get help on the options that have to be supplied (you can also do it through env vars).

I haven't spent too much time on the aesthetics of the project, because it was supposed to be 2 hours tech test.


Time report
===========

I have spent 2:05 coding, this includes learning the mailchimp API, containerizing, creating the command line, trying 4 scenarios (no previous data, one deletion, one addition, no changes). It would be cool to have written tests, but I am afraid I don't want to spend more time on it right now.

I have spent 3:11 writing this document, as I had to go over it several times because I wanted to give a proper proof of how I would work.