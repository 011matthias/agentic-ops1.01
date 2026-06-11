# Brisken Call Transcript — 2026-06-11

**Participants:** Dirk Neumann (Brisken owner), Matthias Neumann; Chris's
input relayed by Dirk ("we just discussed with Chris").
**Project:** Brisken Expense Reconciliation (ACTIVE)
**Source:** Raw transcript pasted by Matthias into the work session
2026-06-11. Primary source — do not delete. No speaker labels or
timestamps in the source; speaker turns are separated by paragraph
only and MUST NOT be re-attributed by inference (see
feedback_session_logs_attribution). Companion extraction in
`context/2026-06-11-call-outcomes.md`.

**Topic:** Walkthrough of the current Zoho Expense + Zoho Books process,
where the historic data lives, FX matching guidance, and a redirected
target architecture for the tool.

---

So I put it in English.
Yes.
All right, go ahead.
Yeah. So were discussing the. Or reviewing the process once more so that you can define which data we need to actually get from expense and from Zoho books. So for the expense recognition and for the bank statement or card statement reconciliation. So we just discussed with Chris, that's first the element in Zoho Expense, which is important, which is the report. The report is basically what the Inland Revenue needs for their audit, or we need to keep, for the audit purposes as part of the documentation for each trip, for each expense, because not only we need to record the expense itself, but also why we actually had the expense, and that is recorded in the report.

So the report will be for a trip, for example, explaining exactly why we had a trip to Italy for a conference, for a business meeting, for a customer visit or whatever. Then the report will document the starting time and date of the trip and the end time and date of the trip, and then all expenses assigned to the trip will be part of that trip, basically. And that's called an expense report, and that is a fiscal necessity. For the complete documentation of expenses, of travel expenses, we at Briskin, we have a second type of report, which is really our administration expense report. We could call that for technical reasons. It's the bucket we use for each month. And we throw the administrative expenses from the cards into those reports.

There's one report for each month, and then there's not. That's. That's not a fiscal requirement because there's basically, there's the cloud costs, there's the LLM subscription costs, there's marketing. Anything that was paid with the card basically goes into these administrative reports. We have exactly one per month and everything goes in there, regardless from each card. Now, from a process, then the reports exist, or Chris creates the necessary reports and then starts scanning all the receipts or sends the receipts into Zoho Expense via email for admin. Usually it's a payment receipt that comes in by email, and whoever gets it from the provider, like myself, Dirk or Chris, and we are getting these expenses by email. We send them directly to an email inbox from Zoho Expense, which creates automatically the expense in Zoho.

Others, which are paper receipts, they are recorded by scanning them. And then Zoho Expense will automatically try to identify them, classify them, and then stores them as unassigned expenses. And then basically there will be a big list of expenses in Zoho Expense, the receipts attached, all the information that could be recognized until then. And then Chris goes ahead and actually assigns these expenses to the reports. And it will. Chris will also go through each expense and ensure that all the information has been recognized correctly and all the fields and classifications and attributes have been filled completely. And by the end of the process, we have basically all the expenses recognized, categorized, classified and assigned to expense reports.

By manual work from Chris through manual,.

Mostly manual work from, from Chris. Now that is only the expense recognition process. We now have complete expense lists with the receipts, with the classifications, reports and everything else. The next step is really the bank statement or card statement reconciliation. The card statement reconciliation happens manually and in Zoho books. So basically Chris has online or through a download, she knows the bank statement in Excel or online. And now she goes ahead and actually creates every single expense manually in Zoho books by taking the expense receipt picture, attaching it to those who expense.

That can be done by drag and drop from expense into books by creating the expense in the same in the correct GL account for that bank statement for that card in Zoho books gives the classification, which is in Zoho Books, the GL account. We have one GL account for each expense classification. They are mapped one to one and filling in the rest of the details and what should be there is basically the same information, pretty much the same information that we already have in the expense. We would also want to see in books, including the report ID in expense, because that is basically the link back to the fiscal information for travel expenses. And that basically is the process today.

Great.

Okay, so now where do you find the historic data, for example, expense recognition? Well, there is a download CSV or.

Something, whatever you can get out of the bank statement as a file.

No, no, that's not, that's. We still. That's not the bank statement. So the expense recognition, that is an expense and you can just download it from there. You could download all the expenses together with the URL to the receipt. You don't get the picture in the download, but you get a real URL to the picture in the download.

And those are the reports, those would.

Be the expense reports. Basically you can see all expenses together. And one of the fields in the expense will be the report and also the URL to the picture of the receipt that was taken. That, that is one thing. So that would be the expense recognition history. Now you can see the receipt. You can see what data was extracted from that receipt. Now for the card statement reconciliation. Yeah, you could download simply the card statement, the complete card statement from Books. So all the entries on the GL accounts with all the references that are in there. So by doing that and then linking it to the data from expense, you should have a, a good matching mechanism. Now, in this process, what we discussed earlier, the difficulty will be the amounts.

So all of our banking cards today are US dollar accounts, US dollar cards. So when we have US dollar expenses, it's not a problem. The amount on the receipt will be the same that appears in the bank statement, in the card statement. But if it is a foreign currency, non US dollar expense, then the receipt will show usually the euro amount. Sometimes if you can get it from the receipt already take the dollar amount. Sometimes that is available. So whenever you find the US dollar amount on the expense receipt already take it because that is going to be the one that also appears on the card. Otherwise you can only guess the US dollar amount.

And the best guess for the US dollar amount is to take the current date, so the transaction dates exchange rate and translate the foreign currency amount to the US dollar amount on that day with the currency with the exchange rate of that day of the transaction date. So that is the best guess. Now Zoho expense has some internally stored rates and they are not very accurate. So whatever the Zoho expense US dollar amount is for a foreign currency expense is an inaccurate US dollar approximation. That causes an issue when you try to reconcile with the bank statement, with the card statement, because on the card you will see a US dollar amounts related to foreign currency expenses, which is the one that was actually booked and that is the true amount that we need to get to.

Whilst in expense you will see a US dollar amount that is different. So the matching buy amount will be hard. So the foreign currency amount of course will always be different from the US dollar amount and even the US dollar approximated amount will also be different. But if we calculate that amount ourselves, we get closer. And then we could try to use vendor information, all sorts of other information to actually do a matching including the amount, but the amount we will have to go in, I would say in rounds, try to find everything that is the exact same amount first, but then start increasing the margin of error.

Yeah.

So then that way you can circle around and check whether and try to find some sort of a way really identifying the correct expense to the correct line item on the credit card statement. Any questions?

No, sir. So the bank report is extracted from books and not from like a bank statement that you receive monthly.

From the bank directly? No, for the purpose of filling the Historic, providing the historic data, you extract it from books. Now in the process, the bank statement or the card statement comes from the bank. So there's two ways we could connect the bank directly with Zoho Books, which we had in the past, but now we don't. And then it updates and fills the bank accounts in books directly with the data. So you have all the entries there. But now we do it differently. We download an Excel for the bank statement or the card statement that gives Chris all the line items and the exact amounts that need to be booked into books. Yeah, but today the creation of the expenses in books is manual.

Okay, but then the amounts are in the Excel and then that can be used for the comparison of the values.

In the reconciliation process. Exactly. So those are the amounts that must be used for the posting in books. And the end results simply are journal entries or card statement entries in books with the correct amounts with the correct expenses, meaning classification, meaning the correct GL account and all the additional information to it. And maybe the cross reference to the more detailed expense table that you have. But I would imagine you can just manage it in a single table. You have a single big table where the report is just another classification. Now you have a separate table for reports, but you cross reference the reports to the expense through just a cross reference field. And where you have already the GL account defined as well, if it's a different name.

But right now it is the same names actually for the GL accounts in expense and in books should be the same at least. And you could. You have different amount fields. Basically. I don't know where you want to start, whether you would rather start with the bank statement and find then the expenses to match them to or the other way around. So you will end up having two tables, in fact maybe three. So you have your expenses as you recognize them and do your work. The download from the bank and the third table where you actually combine them all and everything, whatever is in the third table is the matched and correct data.

It's important the value.

And from there you can export the information to Zoho Books. Yep. And the fourth table is the one for the expense reports.

All right.

Is that feasible? Now a big question though is it worth doing this? Because I mean we do have expense, we do have books. Is there maybe a way to just simplify and improve the actual tools themselves? I know we want to get rid of the tools.

You can integrate an API key from your LLM to books, which is what I did on your test Account that you gave me, and then it can actually perform actions in your books, to which extent I'm not really sure. They already lost it.

So the idea could be that you automatically integrate the bank statement in books and then you have a process running that can reconcile books with the expenses and attribute to whatever was posted in books as raw items. Just go through them one by one.

Thing is, I think you guys can.

Find the receipt for it.

You guys have the security risk of attaching an LLM key to your books with a bunch of.

Yeah, we have lots of LLM things in books already.

Are you there?

No, we're only using pro accounts. So as long as we're using pro accounts, we're fine. We can use it. It's not a problem.

Okay.

That's an approved thing. And once we're done testing, we can document that and make sure that.

All right, then let me work this through and come back to you with answer on what the better path is. If it's worth it to do the three sheets that we then inject into.

I mean, you must imagine the expense is there is built to manage many people's expenses. We only have very few people, that's me and me actually posting expenses. Now that Nicholas has a card, I mean, for each card, basically there might be a person, but it's very limited. And then we have all the admin expenses going through it.

Which is why I think the best idea is to maybe for now have the system be, you know, like cooperate with your Zoho tools. But the long term projection of the, of this tool should be really to gain independence from tools like Zoho that are more adequate for more volume, for lower volume, for higher volume than what you have.

I mean, the tools are for higher volume and we go back to something simpler. Exactly. Yeah, exactly. So for now, for example, you don't worry about the ingestion. The input comes from Zoho expense. The Zoho expense scanner, everything that basically Zoho prepares for us already, we simply accept. What people stop doing is the manual processing in Zoho expense. We scan everything. We just have to make sure that we scan everything. And then the tool comes and does all the classifications and stores it in a separate table instead of having Chris doing it manually. Exactly. And then you, you need to somehow, of course, keep control of what's already in the tool and what's not in the tool. But expense must be the.

If not the single point of entry, but the main point of entry. For now, I Mean, we can for now agree that this is a single point of entry. So whatever we do, we always chuck it into Expense, send an email to Expense, then do it manually in Expense. If it's just then, because you can just take scanned documents, anything, just upload and then Expense does the rest. And we could then move from creating the reports in Expense to creating them directly in your tool. Yeah, doing them in Expense would be redundant. So very simple. Look at, look at what Expense does and just take the necessary piece. It's a single table that. Four, five fields, that's all we need. And then you process the expenses. Yeah, but.

Yeah, but then the easiest is really, I mean, you don't need books for the input for the bank data you get, take it directly from the bank as an upload, as a CSV upload. In the future you can think about connecting directly to the bank. But I guess that's a little bit more complex. Not technically, but from an approval point of view that the bank lets you in. Or it might be expensive because of the subscription to these services that connect to the banks and it might be actually costly that you have a minimum charge of a few hundred, a few thousand dollars or something. So that wouldn't make sense.

But just downloading the CSV, chucking it up into the tool would have to do some basic validations, some duplicate check statement numbers and everything else that the file is technically in a good state. And then upload it just in your bank statement table. You can have a single bank statement table for all bank statements from all banks because you have a bank key, you have bank number, account number, card number and all of that. They can be all in one single table. Then you just join the two and from there you make a single output to Zoho Books. So what Chris now keys in manually, you can actually do automatically. The big question here, I would think is how do you handle pictures?

So ideally you have a means to actually upload the pictures into Zoho Books, ideally. So I don't know whether that works either way through the API. Yeah, because. And even here, I mean, yeah, you probably here you could. It's probably if you get the URL, you can just have another turn and they take the URL. Load the picture into your app. Yeah, if you needed to. Yeah. And. Or at least maybe, but better. Yeah. In your app then you have a URL for each picture in your app, what you can, could then do is just load the URL into Books so the picture stays in the application and the only thing that Books gets is actually the URL to the picture, like here, like in the expense.

And that way in the future we can also switch off books.

True. I think that's a good idea.

Yeah, perfect. That works. And then the first thing you could switch off would be expense by just creating a scanning tool which directly loads the picture in the tool, which then the way we are managing it right now would be the same. So downloading from expense right now and creating a URL location for each picture in the tool in the future, scan directly into that location and have a URL for it. So it's a directory replacement. And then when we tackle books or the direct banking connection and stuff, nothing changes. Sorry. I'm a software design freak. I'm a process design freak. Anything. Okay, so. But this is not all old school. So any improvements that you see because we are native AI, please let me know.

Okay?

Yeah. So this is from a. From an kind of analog relational database world design. Now if that can be improved somehow by using newer technology, newer database logic, the whole thing with AI and attributions and stuff, maybe there's steps we can forget. Yeah, I think for example, maybe something storing data, maybe not in that much stuff in databases, but more in MD format files. Every expense could be an MD format file. And that is maybe easier to access than tables file tool for AI.

Especially for AI.

Just think about it.

Okay, that will do.

All right. I'm looking forward to this.

Me too.
