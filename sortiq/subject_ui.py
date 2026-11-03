"""Local-first subject vocabulary editor."""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

class SubjectManager(tk.Toplevel):
    def __init__(self,parent,vocab,path,on_save):
        super().__init__(parent);self.title('SORTIQ — Smart Vocabulary Engine');self.geometry('770x490');self.transient(parent)
        self.vocab=vocab;self.path=path;self.on_save=on_save
        self.name=tk.StringVar();self.limit=tk.StringVar(value='100');self.status=tk.StringVar(value='All subjects and vocabulary stored locally. Internet lookup is optional.')
        ttk.Label(self,text='Smart Vocabulary Engine — My Subjects',font=('Segoe UI',13,'bold')).pack(anchor='w',padx=15,pady=12)
        frame=ttk.Frame(self,padding=12);frame.pack(fill='both',expand=True)
        left=ttk.Frame(frame);left.pack(side='left',fill='y',padx=(0,14))
        self.list=tk.Listbox(left,width=34,exportselection=False);self.list.pack(fill='both',expand=True)
        self.list.bind('<<ListboxSelect>>',self.selected)
        ttk.Button(left,text='New Subject',command=self.clear).pack(fill='x',pady=8)
        right=ttk.Frame(frame);right.pack(side='left',fill='both',expand=True)
        ttk.Label(right,text='Destination subject folder (e.g. College / Marketing)').pack(anchor='w')
        ttk.Entry(right,textvariable=self.name).pack(fill='x',pady=6)
        ttk.Label(right,text='Keywords and phrases (comma separated)').pack(anchor='w')
        self.words=tk.Text(right,height=10,wrap='word');self.words.pack(fill='both',expand=True,pady=6)
        ttk.Button(right,text='Save Subject',command=self.save).pack(fill='x',pady=4)
        opt=ttk.Frame(right);opt.pack(fill='x',pady=4)
        ttk.Label(opt,text='Online keyword cap:').pack(side='left')
        ttk.Combobox(opt,textvariable=self.limit,values=['50','100','250','500','1000'],state='readonly',width=8).pack(side='left',padx=7)
        self.search=ttk.Button(right,text='Find Related Terms Online (Optional)',command=self.enrich);self.search.pack(fill='x',pady=3)
        ttk.Label(self,textvariable=self.status,wraplength=720).pack(fill='x',padx=15,pady=6)
        ttk.Button(self,text='Close',command=self.destroy).pack(anchor='e',padx=15,pady=7)
        self.refresh()
    def refresh(self):
        self.list.delete(0,'end')
        for s in self.vocab.subjects:self.list.insert('end',s['category'])
    def clear(self):
        self.list.selection_clear(0,'end');self.name.set('');self.words.delete('1.0','end')
    def selected(self,event=None):
        ix=self.list.curselection()
        if not ix:return
        s=self.vocab.subjects[ix[0]];self.name.set(s['category']);self.words.delete('1.0','end');self.words.insert('1.0',', '.join(s['seeds']))
        self.status.set(f'{len(s["seeds"])} seed keywords; {len(s.get("discovered",[]))} discovered terms.')
    def save(self):
        try:
            self.vocab.set_subject(self.name.get().strip(),self.words.get('1.0','end'))
            self.vocab.save(self.path);self.refresh();self.on_save();self.status.set('Saved locally. Scan to apply new vocabulary.')
            return True
        except (ValueError,OSError) as error:
            messagebox.showerror('Subject error',str(error),parent=self);return False
    def enrich(self):
        if not self.save():return
        name=self.name.get().strip()
        if not messagebox.askyesno('Online vocabulary discovery',
           'Only this subject name and the seed keywords you entered will be sent to Wikipedia Search.\n\n'
           'No files, filenames, paths or document text are uploaded.\n\n'
           'Results are candidate keywords and may be incorrect. Proceed?',parent=self):return
        self.search.configure(state='disabled');self.status.set('Searching Wikipedia. You can keep working offline after the search.')
        def worker():
            try:
                n=self.vocab.discover(name,int(self.limit.get()));self.vocab.save(self.path)
                self.after(0,lambda:finish(f'Added {n} candidate terms. You can now scan your folders.'))
            except Exception as e:self.after(0,lambda msg=str(e):finish('Lookup unavailable: '+msg+'; saved keywords still work offline.'))
        def finish(msg):
            self.search.configure(state='normal');self.status.set(msg);self.on_save()
        threading.Thread(target=worker,daemon=True).start()
