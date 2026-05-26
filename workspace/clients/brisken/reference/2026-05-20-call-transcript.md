# Brisken Call Transcript — 2026-05-20

**Participants:** Dirk Neumann (Brisken owner), Matthias Neumann
**Project:** Brisken Expense Reconciliation / bookkeeping platform (ACTIVE)
**Source:** Fireflies recording. Primary source — do not delete. Companion
extraction in `context/2026-05-20-call-outcomes.md`.

**Substantive windows:** project content runs ~21:00–28:52 (then a 15-minute
break) and resumes 01:28:26–01:58. Material before 21:00 is Upwork
navigation, WhatsApp/link setup, and note-taker checks, not project content.

---

Dirk Neumann: 00:00
 Perma delay.  Yeah, you didn't link effect of WhatsApp.

Matthias Neumann: 07:40
 Hello.

Dirk Neumann: 07:56
 Hello.

Matthias Neumann: 08:16
 This is the link.

Dirk Neumann: 08:17
 it's the z.  Okay.  Okay.  Okay.  Yeah you hear the deal of noat fo icloud.  Okay no props.  Is a job often just job postings.  Of them dashboards.  Okay.  Also does this website is a room springt the upwork website.  Okay.  Contract 2 days ago last activity.  Backend timesheet.  M. Just for the sake of it.  Okay.  Messages.  Okay.  Work.  We will need two, three weeks to test again.  Okay.  Is business really here?  Matthias Neumann Arbeit Mitrig Neumann.  This notations are dodgy.

Matthias Neumann: 13:20
 I don't know this project.  Yeah.

Dirk Neumann: 14:40
 The.  Billing summary for Briskin.  Office handyman.  Okay.  Not in bill income.  Ab.  New weekly summary new time sheet.  Learn how to dispute how to find a dispute about our freelancers hours reason article select Dispute is your billing period.  Enter the amount you want to dispute, select the reason.  Certainly you've read and understood the hourly paid in protection terms.  Choose submit.  And then these dispute specialists will come in.  So the dispute page from then the articles.  Good.  Then.  Then I made some.  Some.

Matthias Neumann: 20:34
 Yeah that's very good.  Because I think the Fireflies is listening in English.

Dirk Neumann: 20:50
 All right.  Share anything to look at.  Huh.

Matthias Neumann: 21:00
 So I have a couple questions for you and I think like starting off, I just need to know if the tool that you're building or that we're building, if the scope is to be.  For it to be marketable in the future.  So if you want to turn it into some sort of, you know, product.

Dirk Neumann: 21:30
 Yes, the idea is to.  To be able to turn that into a product at some point.  But it's not the first priority.  First resolve our issue.  But if you can, if you need to make certain architecture decisions that will make this possible to turn it into a product, then we should take those.

Matthias Neumann: 21:50
 Okay.

Dirk Neumann: 21:51
 But anything we can do later, we'll do it later.

Matthias Neumann: 21:55
 Okay.  So yeah, just because a.  Like a build that's just the simplest thing that works and then.

Dirk Neumann: 22:09
 The cell.

Matthias Neumann: 22:10
 Later aspect is just completely different from the foundation on day one.  Actually pretty good that I don't have to take any notes.

Dirk Neumann: 22:27
 Yeah but.  But let's think about it.  I mean the.  What does it mean to be marketable as a product?  It really means that we need to put it on a.  We need to create a multi tenant application with login authorization and.  And things like that.  Right?  Yeah, but login and authorization we need anyway even if it's just for us and even if you have just two users, let's say Exactly.  Yeah.  So then it's only the multi tenancy and that, I don't think that is very complex to architecture.

Matthias Neumann: 23:07
 Yeah.  So.

Dirk Neumann: 23:11
 Because then if you think about it, we already have different legal entities.   okay.  No, sorry, that's, we need that anyway.  That's not the, that's not the multi tenancy.  Go ahead.  What were we going to say?

Matthias Neumann: 23:25
 To a certain degree, I think you're right that the build from the start is going to be just like a different dimension of what the build at the end has to look like.  But I think there's just certain technicalities like the tenant ID or the, the data separation between each tenant that you can strengthen from the beginning.  Right.  Because I think it's not going to be a bad aspect starting out and it's going to be absolutely necessary later.

Dirk Neumann: 24:12
 Yeah, yeah.  So I would say then let's, let's decide that now.  So we build it as a multi tenant.

Matthias Neumann: 24:17
 Yeah.

Dirk Neumann: 24:18
 Application.  Okay.

Matthias Neumann: 24:25
 Then you have a list.  Yes.  I need to know what the.  I'm pretty sure you keep your currency in the books in dollars.  Right.

Dirk Neumann: 24:37
 Now we have to differentiate.  So there's this payment currency, that is the currency in which actual payments are made and then there's the account or card currency, that is the currency in which an account is held.  And then there is the legal entity currency or the book currency, that is the currency in which the legal entity.  So the company does the bookkeeping where they basically report taxes.

Matthias Neumann: 25:13
 Okay.

Dirk Neumann: 25:14
 Yeah.  So in our case, the, the transaction currency could be anything.  Yeah.  So if I'm in Israel or I'm in Europe or I'm in the US or I'm in Russia or whatever, then the currency will be different.  The transaction currency and the account currency is for cards is usually $.  But then we have Europe Euro accounts.  You have pound sterling accounts as well.

Matthias Neumann: 25:46
 Okay.

Dirk Neumann: 25:47
 And, and then the company code currency, if you only look at the US entities of course is all, it's all $.

Matthias Neumann: 25:59
 But now primarily focused on the bookkeeping.  It's also $.  Or do other currencies also pop up every once in a while?

Dirk Neumann: 26:14
 Oh, the book currency never changes.  So do you create a legal entity and that is just your book currency?  Yeah, you don't change that.  So that is dollar.  I mean we have the GmbH, the German entity.

Matthias Neumann: 26:27
 Yeah.

Dirk Neumann: 26:28
 But that is not part of our scope.  But now thinking about a product, you of course need to be ready to have the book currency being defined or the Legal entity being defined as anything.

Matthias Neumann: 26:45
 Yep.  Yeah, of course, that, that would count towards the variability that we need later on if we want to productize or monetize this.

Dirk Neumann: 27:01
 Exactly.

Matthias Neumann: 27:06
 So I think.  Yeah, that's actually a good point.  Yeah.  How long exactly are you required to keep records?  And in which country, like, from which countries do tax laws apply.

Dirk Neumann: 27:35
 Sexually?  Good point.  I'm not quite sure.  I think it's seven years in the U.S. you have to research.  But this is true for.  For everything related to expense reporting.  So receipts and reports and everything that needs to be kept for legal purposes somewhere.  Yeah, yeah.  So that's.  But it's every.  It'll be.  Then basically, you need to have a legal entity with a jurisdiction, with a tax jurisdiction, and then automatically for that jurisdiction, define the.  The storage of the data.  Or we do it differently.  We store it always for like two years, and then we.  We offer backup services, which they can buy separately.  Yeah, you just dump it all in a.  In a local database.  Yeah.  Can we.  Can we continue in 15 minutes?  Sure.  I need.  I need to step out for 15 minutes.  Sorry about that, but you can already work on what we.  What we discussed.  Maybe check whether your.  Your recording tool works and the note taker.  Okay.  And then we get together back in 15 minutes.

Matthias Neumann: 28:52
 All right.  Same link.

Dirk Neumann: 28:55
 Okay, perfect.  Sorry about that.  Yep.  Talk in a minute.

Matthias Neumann: 29:03
 Bye.

Dirk Neumann: 01:28:26
 Hello?  Matthias.  All right.  Yeah, sorry about that, but.

Matthias Neumann: 01:28:55
 Yeah.  So where were we?  Where were we?  All right, the questions.  Where did we left.  Leave off?  You answered the.  Legal part.  How long you have to store data for legal reasons.

Dirk Neumann: 01:29:28
 Matthias.  Matthias, Pretend I'm your customer.  Pretend I'm your customer.  You got to be on the.  On the tip of your toes.

Matthias Neumann: 01:29:40
 Right?  So when an expense is approved,.

Dirk Neumann: 01:29:52
 How.

Matthias Neumann: 01:29:52
 Should it land in Zoho?  And does the receipt have to travel with it?  And one more question with that.  Are you willing to grant a Zoho Books connection, like an API for my system, plus admin access to custom fields?

Dirk Neumann: 01:30:27
 I'm not quite sure and understood.

Matthias Neumann: 01:30:31
 Because in order to integrate the solution into your system, we're going to have to plug it into Zoho or just create a different solution.  As in sheets or something similar.

Dirk Neumann: 01:30:49
 Well, I mean, as I said, I think in the specs, the.  The connection to Zoho expense is.  Is also Books, really is temporary, that could eventually be replaced by our own Briskin Books.  So for now, the.  The integration needs to be there because Books, Zoho Books is our book of records.  That's our accounting management reporting system.  Really?  And the content or whatever is in Zoho books we send to our accountant so they can do their tax reporting or our tax reporting rather.  But eventually we want to switch that off.  So the extension of okay, brisk and expense is really brisk and books.  Yeah.  Where we now integrate all accounts, not only credit cards and do the bookkeeping.

Matthias Neumann: 01:31:45
 Yeah.  Yeah.

Dirk Neumann: 01:31:46
 And.  And that is also why I see maybe.  Maybe the calling it expense to start with.  Maybe it's.  It's wrong anyway.  Yeah.  So because the only difference between the expense system and the.  The bookkeeping system is that an expense it has a category and a bookkeeping system has double entry from between a bank account and an expense account.  Yeah.  So the expense system says Our credit card 2838 had an expense of category A. Yeah.  And now.  And now we have a receipt.  We have the justification for the expense date reasons, things like that.  And.  And then we send it to the books and we're booking it against the credit card account and the expense account A.  So we have a GL account in the booking system for credit card 2838 and we book it there and at the same time we book it against the expense account.  But that's the only difference.  So really our expense report and the bookkeeping system kind of the same.  It's just a matter of how you pull the report.  And maybe that's something we want to think about from the beginning.  Yeah.  And then the integration to Zoho Books here we need to think what.  What that really means.  I think it's.  It's simply a replication.  So we have in fact we do the complete entry or record keeping in our tool.  And now we have a one to one integration between the.  The.  The journal entry effectively in our.  In our application and send that one to.  To Zoho do a mapping of our GL entries to the gl.  The GL accounts or expense categories to.  To the GL account in.  In Zoho Books.

Matthias Neumann: 01:33:47
 Okay.

Dirk Neumann: 01:33:50
 And.  And of course do you.  I give you access to.  To books admin access to all books.  And then you can take it from there.  Basically find the APIs.  APIs for.  To send the journals.  The authentication.  Maybe you can set up some other web hooks, whatever.  There's plenty of things that can be done in Zoho, but the goal is your notes taker actually taking notes because it's on mute.

Matthias Neumann: 01:34:21
 Yeah, it's supposed to be.

Dirk Neumann: 01:34:23
 Okay, so it's just not talking to us, but it's listening.  Okay.

Matthias Neumann: 01:34:28
 No, I forgot what I was gonna say.  The goal is to become or to lose Dependency on Zoho Books or just generally Zoho, right?

Dirk Neumann: 01:34:42
 No, no.  The goal is to create a process that is faster and less painful than it is today.  Yeah.  So today the, our bookkeeper spends days updating expenses and books and reconciling credit cards and bank accounts in a process which should be 15 minutes a month to review it and check that it is okay.  So that process should be 99% automated.  There's no reason why we spend so much time doing this.

Matthias Neumann: 01:35:20
 Yeah, yeah.

Dirk Neumann: 01:35:21
 And rather than building the automation into Zoho, I think we should just build our own little tool and then we don't need Zoho at all.  Yeah.  Oh yeah,.

Matthias Neumann: 01:35:36
 We had that when we were talking one one because you had mentioned that your volume internally isn't anywhere close to large enough to have to implement great big systems and that scaling back could actually be the solution to your inefficiency problem.

Dirk Neumann: 01:36:03
 Yes.  I mean, I don't think we save money.  I don't think bill save money.  The, the Zoho subscription only Zoho books costs us six or eight hundred dollars a year.  Yeah.  And, and it gives us functionality for far more than we need it.  It's a true bookkeeping system.  But we don't do bookkeeping.  Maybe it's our fault as well.  Maybe we should and save money on the accounting side.  But all we do, we use it as a management system, a management reporting system.  So we want to know for what type of expenses, maybe spend our money, maybe want to have a place where we can record bills and invoices and maybe even create them as we do today.  And so we create the invoices in Zoho, then we download them as a PDF and then we send them as an email.  Now could we send them directly from Zoho?  Yes, we could.  Could we do more automation in Zoho?  Yes, we could, but it's everything is more restrictive.  Yeah.  So we always work inside a predefined structure in a very, in a large system.  Just imagine we're going to be faster for the little requirements that we have in our own tool.  If you have a glorified Excel spreadsheet or spreadsheet, that'll be nearly enough now that we are building an app.  Of course I don't think we should have a spreadsheet only, but we should probably have something like a spreadsheet type of view of our data where we can mass edit and quickly edit the information validated.  But maybe basically the maintenance of it all is easier.

Matthias Neumann: 01:37:53
 Yeah.

Dirk Neumann: 01:37:54
 Right now it's a pain in the back to.  To.  To make any mass changes to reclassify.  And it must because it's an ERP system.  It's a structured, highly integrated ERP system.  But we do not use all that integration.  We don't use all the functions of Zoho books.  So all we need in the end is exactly what we're doing in the expense reporting.  Read bank statements or credit card statements, classify those entries in the bank statements and the credit card statements guarantee that we have reconciled, meaning that we have captured and classified every single transaction on the bank statement or on the credit card statement.  But we don't miss anything.  So that is important.  So that always the bank and our reports are in sync so it's not a single transaction lost.  And then that we basically run reports on the classification, which we then call GL accounts.  And that we have an easy way to define these GL accounts.  It's a structured way of defining them.  So there's basically, there's main accounts and then there are sub accounts and there might be sub.  Sub accounts.  And we can reflect that in our reporting structure.  And that's pretty much it.  Then maybe some easy features like issuing an invoice.  So it's like a template you can quickly fill in and then you issue an invoice like we can today.  But that's really no rocket science.

Matthias Neumann: 01:39:34
 Yeah.

Dirk Neumann: 01:39:35
 So rather, going into SoHo, we have a little screen or maybe a table.  Better than a screen.  I think you just have a table where you put all the data that you need for the invoice and pop.  It makes an invoice.  Yeah.  And if you agree with the invoice, then it books the invoice to some holding account from where then the bank statement comes in.  It first checks whether there's an invoice open that.  That.  That needs to be attributed or does.  Does other stuff.  Okay, but, but right now we're looking only at credit cards.  So the logic of credit cards is that there's never an invoice first.  Yeah, a credit card is always a.  Or expense is always.  Basically you're creating expense and feeding whatever's on the credit card at the same time.  Nearly.  All right, well, no, I said that wrongly.  It's, it's.  There are no invoices for expenses.  But what you do is usually the bank statement comes after the expense was created.  So.  But it could go either way.  So it could be that I'm, I'm buying, I'm buying a pretzel at the store.  I pay for it with a credit card.  Now I get a receipt for it.  The, the receipt I want to easily scan and leave it with the system to, to, to create it.  So basically I scan it and the system automatically creates that expense.  It ideally it can identify the classification automatically if it finds the amount, the currency, the date, the vendor, and maybe some additional information.  Now of course the credit card that was used, it must be, must recognize as well and then any other information, invoice, number, reference numbers, whatever it can find that it's simply, that's a scanning exercise.  And then creating a structured entry in a table for an open expense.  Then either a minute later or weeks later, the bank statement comes in, the credit card statement comes in.  And that could be really a daily process.  We could every day we could actually go to the bank, get all the credit card entries for that day or anything that we haven't had, haven't integrated yet.  We get every new transaction.  We could ping it every minute, real time.  Because all the time try and find on the bank side whether the entry that for which I have just created the expense already shows up in the, on the bank site.  Grab it, download it, reconcile it.  Done.  But it could be that this process is separate as well.  It could be that the bank takes on the card.  It takes two or three days to appear.  So we now have created the expense, it is in the table, it's waiting and days later, whatever time later on the credit card statement, the entry appears and we want to match it now to the expense we have on file.  We have the expense record, we do have the attached PDF or scanned receipt in the record as well.  And now that comes the bank statement and we want to match them exactly.  So we need to match it.  Yeah.  Now we have the matching has various levels of difficulty.  Usually if it's a US dollar card and US dollar expense, if you just take the amount and the date, you get a 99% hit rate because amounts usually are different.  Then you have vendor information or all sorts of other things.  As long as the currency is the same.  The real problem starts when you have a euro payment on a US dollar card, then your receipt is in Euro but your expense on the card is in dollars.  So the amounts don't match.  Yeah.  And then you need to basically be creative.  You have to look at other things.  You have to maybe do a, a mock conversion.  You convert the receipt Amount to dollar and use that as an approximation of where roughly the amount should lie.  Because the credit card agent or the bank is going to use a different exchange rate than whatever we have in the system.  Yeah.  So you can only approximate it, but then you have to go for vendor information, for receipt references, for whatever else there is in order to do the matching of the bank statement or the card statement, line item and the expense.

Matthias Neumann: 01:44:20
 Which leads us to my next point, which is exactly the fact that I need to ask you for permission to basically train the LLM system that we want to build into this tool on your current data.  So, for example, exactly those types of transactional matches that have, I mean, we.

Dirk Neumann: 01:44:52
 Have, we've done this all manually over the last five years, so there's tons of data available.

Matthias Neumann: 01:44:58
 Okay, perfect.

Dirk Neumann: 01:45:01
 And then it's not the LLM you're going to train, it's.  It's your system.

Matthias Neumann: 01:45:06
 Yes, the LLM is of course only responsible for the judgment calls.  I think it's more over the Python matching part of it that has to be trained.

Dirk Neumann: 01:45:21
 How are you planning to do the matching?  You want to do it deterministic or a pure LLM?

Matthias Neumann: 01:45:29
 No, no, the matching code and the.

Dirk Neumann: 01:45:38
 How are you going to do the.  I mean, the deterministic would be that if I see ABC in a receipt, then I'm going to assign it to.

Matthias Neumann: 01:45:46
 Vendor pattern recognition, similarities, dates.

Dirk Neumann: 01:45:54
 But you're not going to code all the pattern recognition, right?

Matthias Neumann: 01:45:59
 It depends.  That's why it's a lot more efficient to train it on recurring or past data.

Dirk Neumann: 01:46:09
 Yeah, but what do you mean when you say train?  So it's not deterministic?

Matthias Neumann: 01:46:16
 Well, train in that aspect that you could either build the structure to, for the deterministic.  The, the deterministic runs to handle a large volume of different patterns and that type of stuff, or.  But to take your samples and have it run or have it be able to recognize patterns of that similar category.

Dirk Neumann: 01:46:56
 Yeah.  Well, you have to explain to me at some point how you're planning to do that, because, I mean, the idea is that we find some new way of doing this so that we don't go into the, into exactly the deficiencies that Zoho today has.  The matching in Zoho is very poor.  You have to have the exact same vendor somewhere.  It simply assumes that the entries, they're always the same and then it does a matching.  You basically have to manage and update them all manually and create them so it's something.  But at the same time you don't want to use AI for things where you could have a deterministic or an algorithmic matching.  So maybe it's a hybrid that you run the AI on the historic data to fill the matching table.  I don't know.

Matthias Neumann: 01:48:04
 The concept that I chose is basically to have the matching logic, the intake, the receipt intake plus the receipt reading and that type of stuff all in the same language.  So it would all be in Python and FAST API would basically be responsible for the matching processes.  And then you can send past API.  It's just a Python parser structure typically used for these types of processes.  For example information matching and quick data.

Dirk Neumann: 01:48:58
 A parse API or fast.

Matthias Neumann: 01:49:02
 It's named Fast API but it's for parsing processes.  But also these quick processes that run in the background.

Dirk Neumann: 01:49:11
 So okay, until you're basically going to buy or pull in a tool like our One Parser.  So basically you're going to use a one parser to actually do all the parsing and the attribution of the information.

Matthias Neumann: 01:49:28
 A tool.  Yes, but it's, which is the.

Dirk Neumann: 01:49:33
 API of a tool.

Matthias Neumann: 01:49:34
 It's open source code.  Yeah,.

Dirk Neumann: 01:49:38
 You know the, okay, so the, the, the code behind the FAST API is an open source program.  Yeah, but you're going to use it's, is it hosted or you're gonna entire API yourself.

Matthias Neumann: 01:49:55
 Yeah, you host the API yourself.

Dirk Neumann: 01:49:58
 okay, that, okay, then you would be basically improving it and work on it to make it.  Make it.

Matthias Neumann: 01:50:04
 Exactly.  And then that's where you can, that's the step that I mean, where you can then use the real statement files and real receipts that you've already received in the past to improve the system.

Dirk Neumann: 01:50:28
 Yeah, but what is the output of FAST API?  In what terms does it do the matching or does it train the matching?

Matthias Neumann: 01:50:41
 It does the matching.

Dirk Neumann: 01:50:45
 Okay, but then again, so what does it do internally then?  How does it learn how to match?

Matthias Neumann: 01:50:53
 It's not that it learns how to match.  I'm developing this with.  Cloud Code agent and basically cloud code writes into its structure certain variabilities that it has to focus on.  For example, certain elements of a receipt type or statement files or for example.  What you mentioned, the American credit card running transactions in Euros.  Certain elements of that can be incorporated into its parsing code.

Dirk Neumann: 01:51:52
 But hold on, the statement you don't need to parse, it's the receipts you need to parse.  The statement comes in a table or in a JSON or in a File format or whatever, the statement, the card statement.  I mean, of course you could take a paper statement.  You could, but that's not really the purpose.  So we presume that we have a structured format for the statements, the card and the bank statements.  So that is fine.  I mean, the parsing is on the receipts only.

Matthias Neumann: 01:52:32
 Okay,.

Dirk Neumann: 01:52:35
 Yeah.  I mean, later we can also.  That's a different process than to parse a statement would really simply mean to take a statement in PDF or whatever format and parse it into the statement structure.  It wouldn't do any interpretation per se.  It would simply have to make sure that it does all the reading and assigns it all to the right columns.

Matthias Neumann: 01:53:00
 The point is just basically to make the parsing more accurate on Briskin's paperwork.  That's about as simple as I can put it.

Dirk Neumann: 01:53:15
 So, you know, that's fine.  But I want to understand how.  Yeah, I want to understand how we are going to do that.  So yes, you're absolutely right.  We want to make the.  Make the passing most accurate possible.  We want to improve the process.  We want to simplify the process.  So in the ideal case, all that's needed is a mobile phone or any other way of parsing the.  Taking a picture of the receipt and then the engine does the rest of the.  And you don't ever need to look at it.  The only thing that you do in the end, you look at the reconciled statements with the classification and the attached receipts and you can say yep, yep, all correct.  And if you do that 10 times or throughout a few number of months and you trust it, then I think we only need to look at things that the system flags as low confidence.

Matthias Neumann: 01:54:22
 Yep.

Dirk Neumann: 01:54:23
 And have everything else being accepted.

Matthias Neumann: 01:54:28
 So since we're already talking about the tech stack, I remember that from a past project.  I think it was the flight expense filter that I built into your email or something that you use at Brisken.  You use Azuri a lot.  Is that still true?

Dirk Neumann: 01:55:02
 What do you mean a lot?  I mean we are running Microsoft 365 and that's our email system.  Email and then has SharePoint and everything else.  Okay.

Matthias Neumann: 01:55:15
 Because.

Dirk Neumann: 01:55:15
 And I think from an infrastructure Microsoft is running on Azure.  Yeah.  So they are running on Azure.  So basically, yes.  So some of the deep database controls, they are.  They are through the Azure settings.  Okay.

Matthias Neumann: 01:55:34
 Because Azure has a document intelligence which is just basically specifically good at reading receipts and that type of paperwork and also variable in its language input.

Dirk Neumann: 01:56:00
 In.

Matthias Neumann: 01:56:01
 Comparison to other alternatives that can only handle English input and kind of get sloppy with other inputs.  And my idea was since you at Riskin already use Azure, that would be quite a good solution also in its reliability.

Dirk Neumann: 01:56:27
 Quite, quite honestly, I wouldn't go for that.  I mean first, because for Briskly it's not clear whether we're going to stay with Microsoft and second, because it's.  Anything from Microsoft is just too complex.

Matthias Neumann: 01:56:43
 Okay.

Dirk Neumann: 01:56:45
 And third, it's usually much more expensive than anything else.  Yeah.  And if you want to turn this into a product we don't want to, you know, have.  Well, it wouldn't be, it wouldn't integrate with Brisken's Asia.  Right.  So you would have to run it on an Asia related to this platform now.  Right.  I, I presume otherwise we'll be, will become an add on to, to the Brisk and Asia account.

Matthias Neumann: 01:57:16
 I mean, yeah, internally it could run on Briskin's Azure but of course if we want to turn this into a monetizable product then of course it would have to run independently of Briskin system.

Dirk Neumann: 01:57:34
 Yeah.  So.

Matthias Neumann: 01:57:37
 Yeah.

Dirk Neumann: 01:57:38
 So I would recommend to experiment with the Google Cloud platform.  What's it called the Firebase thing that we discussed at some point?

Matthias Neumann: 01:57:51
 Console.  Google Console.

Dirk Neumann: 01:57:55
 I think that was, you know, the entire infrastructure.  So where you're running the back end, the front end.  So the runtime, the database, the.

Matthias Neumann: 01:58:03
 Yeah, exactly.

Dirk Neumann: 01:58:04
 AI services.  Your recording will stop in two minutes.

Matthias Neumann: 01:58:13
 Okay.

Dirk Neumann: 01:58:14
 From what I know, it's called Google Firebase.  Yeah, it's Fire.  It's.  It's called Google Firebase.

Matthias Neumann: 01:58:30
 Okay, I can look into that.

Dirk Neumann: 01:58:32
 I'm mentioning that because that's what be applying to external participants.  Why can't I click on this, paste it here.  So it's called make your app the best it can be with Firebase and Generative AI.  Firebase is a platform of services to help you and AI agents build and run intelligence apps.  Apps with more speed, security and scalability.  Designed for complete app development life cycle backed by Google and trusted by millions of businesses around the world.  Then when you go into it, first you get a free, a free something out of it.  Yeah.  App Hosting, SQL Connect, Firebase, AI Logic, Remote Configuration, Crashlytics and App Distribution Agent Skills, GenKit and they have all sorts of easy integrated teams.  Favorite tools, BigQuery, Google Ads.  Yeah.  So not sure, maybe it's a long way off but I, I wouldn't.

---

## Part 2 — continued recording (~0:00–37:37, no per-line timestamps in source)

All right. Okay. So I can look into Google Firebase as an alternative. Considering the fact that you say that Azure kind of has a tendency to be over complicated and overly expensive, that also kind of writes out another solution that I had in mind which was where we having Azure Blob be the place where we store the original photos and PDFs of receipts because as we mentioned the legal obligation is I think somewhere around seven years or something. And that and Azure would have been. A. Good option, but considering the price restraint. And. What did you write? Oh, considering the price restraint, I'll have to look into an alternative to that as well. Maybe.

Where did you plan to store it? Asia. Asia Blob. Yep. Maybe we could even do something self hosted or. I don't know.

But that is something also on Firebase. I mean if you use Firebase or then really any cheap database, but look for something cheap. Yeah, exactly. Cheap but still secure because it's, it's financial information with personal information, partial bank numbers, bank account numbers and stuff. So you need, for the receipts you need a secure but cheap database.

Yeah.

And, but then you think that you have a database basically the structured data, the receipts and everything else, and then the link to some other place where you're storing the physical receipts, Digitalized receipts.

Yes. For what reason would they be stored in two different places?

Yeah, I'm asking, is that what you're planning to do?

No, no. The plan would be to store them in the same place.

so you basically have a database where you can also store files. Yeah. And that is cheap enough to actually do. Yeah. Okay. Yeah, good.

All right, Quick, I need your confirmation that I'd be using or implementing CLAUDE Anthropics AI into the tool and your confirmation is needed to. That. That you're okay with personal sensitive data going through the a.

Where do you need that confirmation? Sorry?

Well, because it's sensitive data. That's why Anthropic actually was the choice at hand because as far as I know it has quite good regulations for its users data protection. But at the same time. I think. It's not a bad idea to ask if you're okay with that.

Well, the, the app needs to ask that. Certainly. Yeah. Now the account that you're using must be a, an account that does not use the data to train the model. Right. So you cannot use our data or the customer data or the brisken data. Yep. To train Claude. Yep. You use it to claim to train the application, but not Claude. So you need to have a subscription to Claude that is at a level that gives you that guarantee, which is basically any pro type of subscription.

Yeah. And you can deactivate Cloud always asks for permission when you initiate it. If they can use the data to train their own models.

And yeah, they must not. Yeah, yeah. And, but that's a good question. So what type of subscription you should be using? The Brisk and subscription. I have one already now. And you have to figure out whether that actually then you'll be using APIs, you probably need access to that subscription. Yep. And so put that on the, on some sort of a task list so we don't. So that we don't create yet another account and stuff that we use what we already have. Of course, maybe within it we can have a group or something created.

There is of course the solution to have the API hosted by AWS implemented and not a personal API key.

No, but it's not a personal API key.

Well, it's briskin's API key.

Yes.

And I'm saying host the LLM instance on Amazon server. For security reasons,.

I wouldn't. What do you mean? I don't understand. Well,.

As far as I know, the AWS hosts Anthropic servers in the eu. And so for, I think scaling this or just making it already flexible for future monetization, you could say instead of going onto Briskin's personal account, creating an. API key instead of going directly to Anthropic. I mean. Yeah, but instead of using the LLM directly on Anthropic, you're saying maybe you should have and use CLAUDE there. You should be using Claude hosted by aws.

Yes.

And how much more expensive is that?

As far as I know, I actually had this project, the CV generator, where I implemented exactly that into the tool. And the most important part about it was that AWS hosted in the EU has EU data restriction laws making it compliance safe and all that stuff. So the data never leaves the eu and all the other compliance laws and stated by the EU apply to the data that you interchange with the LLM. From the expense part, I couldn't tell you exactly, but it wasn't that big of a difference, if any at all.

I mean, the US companies, so we do not care about EU safety. But, but can't you add Anthropic as well? Choose the data center.

What do you mean? Add Anthropic, choose the data center.

Yeah. So if I'm crawling an API there must be somehow the possibility to Say I want my API to run in the US or I want to run it to run in Europe.

I don't think so.

Or can I create a European user which will run definitely in Europe and have a USer that runs in the us?

I think the API keys created directly on Anthropic all get sourced to the us.

Well, it's maybe something to figure out. Does it look at the user where it's created? Is there a possibility to choose your data center? Does it use the IP from where the request comes to actually select the data center? And what the price difference would between AWS hosted Claude and USing Claude directly on Anthropic? Yep, I think it's a research. But it's a very good point that you bring up because I think yes, if there's an added security layer then that'll be helpful. But at the same time it is, I think for small companies like ours, they just need to choose one. Yeah. So I don't think the Americans. Yeah. So for US customers it doesn't matter whether it's in Europe or in the US as far as I know. Whilst for European customers sometimes it does matter. So we could decide to run in Europe for all customers and yeah, I would imagine that's something we can do. But usually when the volume grows, I'm sure you can manage that. I'm sure you can then say, okay, we are running for US customers or you just choose when you set up the account that they can choose where they want to run. But that's something we can do implement in the future. But, but then again, I wouldn't say AWS as the, as the provider. But then if, if you are on Firebase, check out Firebase because it has the AI hub, the model hub or some, the model selector or something like that. And, and check there whether that's not the same feature that you're thinking of in aws, whether that is a hosted anthropic on Google. And then you have there the same possibility to choose Data center and all the rest. Or whether the Firebase AI hub is simply the orchestrator and then you still use your own API keys to actually put it in there.

Yes, only. Okay, yeah, the. Firebase you said. Okay, but just for the AI hosting.

Oh, for everything that's. Firebase is the platform that I mentioned earlier. Maybe should be building everything. Maybe should have our database, maybe you should have our runtime.

Okay,.

Yeah, it also has the AI whatever portal gateway or whatever they call it, I'm only.

Seeing now in my notes. Firebase tends to kind of get messy and inconsistent for anything that's not a very simple app. I mean, we can try it out, but we'd have to gauge kind of the complexity of our build, especially when it comes to accounting reports, audit trails and that type of stuff.

Yeah, but for example, audit trails. The Firebase has a service that basically creates out of the, out of the box, the audits. It tracks everything. Basically you just have to enhance a portal for that so you can see all the audit entries, so everything is being logged and you can even include the logs into the app. So basically what really is primarily it's a platform tool, the logging and the log reporting, but you can actually call the log reports inside the app so the user, the customer can actually look at those logs and those reports that are relevant to the user. You can integrate that into the app directly. So from that perspective, it actually could be interesting, but you need to do a little bit of research.

All I know is what basically Giuliano tells me, because that's where he's building our one pilot V3, the third version, the third release of our one pilot. He's building on Firebase for the reasons to get everything out of the box. Logging, maybe the AI access we do separately. We don't use the Firebase part, but database, very cheap database access, very cheap runtime, very elastic pricing. So we don't, you don't need to buy big blocks of minimum pricing. But he says that probably 80% of our customers, we could actually stand up as a project and not pay anything because they're so small.

Okay.

So it's something to investigate and if that really works, and maybe it's a good place to get experience in and if it doesn't work, is also a good place to fail.

Okay, sounds good. That would be everything from my side.

Yeah. And functionally you need to work with Chris because she's running this process, so she knows which accounts, she knows the cards, she knows the historic data. She has all the bank, all the cart statements. She knows where to meshi reconcile this data and things like that.

Okay.

And maybe she can share her Zoho access with you. She has admin access to Zoho books to Zoho expense. And then, and then you can, you have full access to the data just.

For the AI's context. Listening. Could you just introduce Chris real quick?

Yeah. Chris is the financial operator. She's our finance manager. So she's operating the process right now for expenses, for bookkeeping, for invoice sending. She's the only finance person in the firm. So she's the key user for this process.

Okay,.

And one more thing. So basically the solution must be capable of managing multiple legal entities. Just, I mean, we touched on the legal entity with regard to the legal entity currency or the book currency. Yeah, but it's important to know that we have multiple entities, so they must be managed separately and the user access must be separate. Right. And they have their own reports. But at the same time we also want to see consolidated reports. So that, that is important. So legal entities is basically a d. A dimension of the system. But at the same time also it is, what is it called? Like rlsa. Relevant. It's one of the fields at which we need to grant access or prevent access to separate users on our account.

Yes.

So from a structure, basically we need to have an account for the app at account level. Now we have of course, the owner of the account or owners of the account, and we have admin users on the account, those that can do the configuration, that can see everything in what's happening in the app. Then inside the app we have legal entities. And then there might be users that. Are. Only allowed to work on specific legal entities and others. There are some, even a legal entity admin, for example, on the legal entity level, we have an admin role that would be a person that can, for example, grant access to other users on that legal entity. That would be a person that can do anything that can be configured or managed on a legal entity level that can be done by that type of user. And then we have, let's say, process users. So those that can create expenses and can operate the system, but they can't configure it, they can't create users. Those would be the, let's call them the finance operators. And then we would have users that can only look at data. They can run reports they can run, they can see the reconciliation results, they can see the data, but they can't enter or change any data in the system. And also the accessibility by, but also by legal entity. And really, I would say it should also the granularity of the access should be also by account. So of course an admin has access to all accounts in the legal entity. But then the operator, for example, offer inside a legal entity has access and does operate only on the authorized accounts. So bank accounts and credit card accounts that the operator is assigned to. So basically you must have a person responsible for a specific account. Then that person will do the reconciliation, will do the booking, will read the bank statements, will do everything that can be done on the account, bank account or credit card account, and the same for the viewer. So there might be a viewer that can see all accounts. And at Brisken, the viewer will be able to see all accounts. But other customers, when we have this granted to others, you can actually assign an account to a viewer so the viewer won't see everything. That's basically the idea.

Yeah,.

But that's relatively simple. It's a simple attribution thing. You have a user at the account level, then you give its role and you give it the scope. So the role is I'm a processor or I'm an admin, or I'm a viewer. And then the scope will be the legal entities and the bank accounts and credit card accounts that the person has access to. So I think those two dimensions we need basically in the definition of the user,.

When you create accounts on the tool, then you can give them certain permissions and admin accounts can take certain permissions away and that type of stuff.

Yeah, exactly. Yeah, but that's basically, it's a mapping table. Now you create them and then you attribute the roles and the data scope to them. So that is important point. So basically multi tenant, multi legal entity and the account sits on the tenant. Yeah, I think that's really it.

All right,.

We need to think about. Yeah, okay, so right now the connectivity to the banks, how do we get the credit card statements or the bank accounts statements? Email?

Yeah, I mean future state. We need to connect directly to the banks and the credit card companies. So that is a must. I mean, without that there's no point actually offering a solution to the market. Okay, so that is a must. Otherwise it's pointless because it will never be automatic. So the idea would be we have a live connection to the banks and we can real time and online we can reconcile the statements. That should work though, I think their. Providers, basically we will not get direct access to the banks. They usually don't give that. You need to be certified and security validated and what have you. But, but you will need to be. You can buy access through providers. There are various providers that give this, this access level there. Some of them they are specialized by geography. So you build certain ones, they're better in European accounts, others better on US accounts, things like that. And, and then some of them, they don't provide all the data, so they may be, they give access only once a day or only in a specific format. So you will have to investigate a little bit what the best access will be. But that is not in phase one. That is not for the mvp. That's long term.

Yeah, yeah. So for the mvp, I would suggest it's simply a file upload and you need to check which formats we can download. Usually it's a CSV format. It's the easiest that we don't even bother about downloading the exact bank formats, but at the same time if we use the bank format, so if you use an MT or COMTI format now, then the online connection very likely uses that format. So we save ourselves the work to do some reformatting or whatever in the future. We need to be able to upload any type of format, even PDFs, Excel, CSVs connect directly to Google Sheets, text file, whatever. So in the future we need all of it. At the very beginning, I think one file format upload is enough and I would suggest we just take CSV or Excel. Basically it depends on what we currently have on the books, what we already have downloaded, whether we download CSVs or whether we download Excel. Because then we can simply take all the existing spreadsheets that we already use and upload that. Yeah, but it's not going to be a very smart application if we don't have a live connection.

Oh yeah, I get that. Yeah, that makes sense.

Then my other concern is the other side of the process. So how do we scan, how do we scan the receipts? It's cumbersome if we have to scan them, create a file and then upload the files that disconnects, complete the process. So I think a simple scanning tool on the mobile phone would be important if that is easy to create. If not, I would actually suggest we reverse engineer in a way. We actually still use Zoho Expense and its mobile application and its capability to scan receipts and we fetch the data from there because then we would have the, we could get the URL of the picture that was taken of the copy of the receipt. We could take that from Zoho actually. Yeah, then we don't need to create our own scanning tool, not yet. I mean eventually we need it, but maybe it's not the most important part right now, but then we have a mobile application which would be Zoho Expense. We can Use that to actually take the picture and to upload the picture in a structured format. So expense would also try to do the auto scanning, but we would want to ignore that. Maybe, maybe use it as a comparative information. Yeah, we can compare what Zoho Expense does and really sort of do something very similar, but to better at the scanning. Yeah, but in any case we can grab the URL and get the picture. I mean, do you have other ideas? I mean, I mean this is just what I thought.

I'm unsure what difficulties building a scanning device or application might bring, but I'm down to figure it out and see worst case scenario. It has to be part of the long term goal either way.

No, no, you can't. It can't. The MVP must be able to scan, otherwise. That's what I mean. Figure it out. Figure out what it takes to create a very simplistic tool that it runs on the mobile phone. It can be a, it can be a website on the mobile phone, it doesn't matter. Now if you can just click a link, it opens a page in your browser on the mobile phone and from there you can now actually operate the camera and take a picture and then upload whatever the result is of that picture. That would be enough. I mean of course if it could do some cropping would even better because then you prepare the file better for the OCR and for the parsing and if that is possible, that'll be ideal. So totally simple. And then you give it a location, it uploads it, and then you know that our app knows in which folder to find all the files online and that'll be perfect. Worst case would be you have to use Zoho Expense mobile app and the files uploaded by Zoho Expense. Now all you would need to do is figure out where does it store them. Now how do we get the URL actually? So we need to have an API to Zoho Expense, read the expenses and get the URL from it. Yes, and just use them as input. So rather than using your own app, you're using Zoho Expense only the URL as your starting point to get the picture for the expense. I think that's the worst case if we can't build something ourselves. I'm sure there's tools, there's libraries, there's something you can just pick off the shelf to get this type of functionality. So if you look for ready made libraries or I don't know, you might call them differently functions or code Blocks that you can just utilize to create this little app. Try lovable to see whether that can do something for you. Because it's separate in a way. It's a separate application only for the scanning on the mobile phone. And so maybe a quick lovable app where you say okay, give me the possibility to scan documents and crop pictures. That'll be enough. Okay.

Okay,.

Let's do it.

Sounds good, Dirk.

Alrighty. Alrighty. I want to see everything that you build of this now. Okay. It's again. What, what is it? What is it you're going to do now? You write the specs. So all right. Is going to come next.

So let's. The, the next choice is basically what's coming next is going to be looking into Google Firebase as an alternative for the Azure installations that I wanted to make.

Yeah, no, but sorry but very first thing you need to write a new version of the functional spec. So basically the document that I gave you to start with, you now need to revise that based on the information that we collected in this call, right?

Yeah, that either one.

And then as a result of that, yes, there are certain researches that you need to start.

No, that either way. So the list of questions that I had were all based on the spec that you gave me and what gaps it left open and hopefully they're all. Well, I'm pretty sure they're all closed now.

But not my honest question to you. Did you actually read it or you just fed it into your AI and ask it? What questions can I ask? No, I read it line by line all the way through. Not that type of reading, but I did go through it, look at the main points.

Yeah, but please read it because you won't if you don't understand fully and into the latest detail what we are trying to do. Yeah, then it's not going to work. It's not based on some AI powered ideas and questions that be that we get this sorted. Yeah, you can't control the AI if you do not understand what's, what we want to do at the base.

No, that's why I think also a pretty good aspect that I could leverage is my proximity to Chris because she, she's like. Well read into the processes concerning this project or this project's field of influence, you could say. So I think that would be really valuable to talk to her about. About it.

Yeah. Okay. Because I, I started with her a little exercise just to find out what capabilities we could easily do. Yeah. And so because of. Of the difficulties in her process, she's taking a long time. It's an awful job. It's. It's annoying, it's cumbersome, It's. It's uninteresting. So we want to simplify her life. Yeah. To free her up to do really, the more value add activities that she's supposed to do. Yeah. So. But we started this conversation. In fact, I started it with her. And from that this new or more defined requirement was actually born,. Which is. In kind of in line with everything else we had been discussing. But it's just maybe a different priority that we put now on expenses rather than the whole of bookkeeping, rather than only parsing, rather than whatever other focus area we had talked about before. All right, you don't. Then let me. Let me talk to Chris first. Were you on your side? And then eventually when she's. She's also briefed, then we maybe have a call together and. And then you basically. Then we should have regular calls or something, which may be. We should have regular calls. Maybe in the beginning, more frequently. Just to check we're on the right track. We are progressing, we're doing. Taking the right decisions and turns. Yeah. And then take it from there. Sounds good. Alrighty.

Thank you for your time, Dirk.

Yeah. Then switch off your. Your agent. And then we finished this conversation.

Oh, yes. Here you go. I don't even know how to do that.

Wait, I kick him out of the call. SS Wait. I have to think.

[Recording ends ~37:37 (part 2).]
