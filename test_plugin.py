import sublime
import sublime_plugin
import re
from functools import partial


class EditCommand(sublime_plugin.TextCommand):
    def run(self, edit,index,insert_string):
        print ('index: ',index,'string: ', insert_string)
        self.view.insert(edit, index, insert_string)

class ScrollCommand(sublime_plugin.TextCommand):
    def run(self, edit,point):
        print ('scroll commanded run')
        self.view.show(point)


def scroll_view_to_region(view,region,pattern):
    print ('scrolling to: ',region,pattern)
    view.show(region)
    view.show_at_center(region)
    pattern_regions = view.find_all(pattern,sublime.IGNORECASE)
    sel = view.sel()
    sel.clear()
    sel.add(region.a)
    view.erase_regions('pattern')
    view.add_regions('pattern',pattern_regions,scope="storage.type")

def get_region_for_show(view,line_num):
    lines = view.lines(sublime.Region(0,view.size()))
    return lines[line_num-1]

class CodeAnalyHelperPlugin(sublime_plugin.EventListener):

    def __init__(self):
        self.files_dict = {}
        self.last_pattern = None

    def check_ext(self,view):
        if view.file_name().endswith('.cth'):
            return True
        else:
            return False
    def analyze(self,view):
        first_line = view.substr(view.line(0))
        pattern_search = re.search(r'Searching \d+ files for "(.*)"',first_line)
        pattern = None
        if pattern_search is not None:
            pattern = pattern_search.group(1)
        
        self.last_pattern = pattern

        #Searching 10472 files for "html.raw" (regex)
        if pattern is not None:
            pattern_regions = view.find_all(pattern,flags=sublime.IGNORECASE)
            #print ('patterns: ',pattern_regions)

        header_regions = (view.find_all(r'(^(\w|/\w)|(\n(\w|/\w)))[^\n]*\n|\s+\.\.(vulnerable|unvulnerable)?\n'))
        header_regions = [sublime.Region(reg.a+1,reg.b-1) for reg in header_regions]
        size = view.size()
        body_regions = [sublime.Region(before_reg.b+1,after_reg.a) for before_reg,after_reg in zip (header_regions[:-1],
                                                                            header_regions[1:])]
        body_regions.append(sublime.Region(header_regions[-1].b+1,size))

        vulnerable_regions = []
        unvulnerable_regions = []
        todo_regions = []
        for header,body in zip (header_regions,body_regions):
            header_str = view.substr(header).strip()

            if header_str.endswith('unvulnerable'):
                unvulnerable_regions.append(body)
            elif header_str.endswith('vulnerable'):
                vulnerable_regions.append(body)
            else:
                todo_regions.append(body)
        
            
        #print (header_regions)
        view.erase_regions('headers')
        view.erase_regions('body')
        view.erase_regions('pattern')
        view.erase_regions('vulnerable')
        view.erase_regions('unvulnerable')
        if pattern:
            view.add_regions('pattern',pattern_regions,scope="string")
        view.add_regions('headers',header_regions,icon='dot',scope="storage.type")
        view.add_regions('body',body_regions)
        view.add_regions('vulnerable',vulnerable_regions,icon='dot',scope="entity.name.tag")
        view.add_regions('unvulnerable',unvulnerable_regions,icon='dot',scope="entity.name")

    def on_activated(self, view):
        if view.file_name() is None:
            return
        if view.file_name() in self.files_dict:
            #открылся файл, который нужно скрольнуть
            target_line = get_region_for_show(view,self.files_dict[view.file_name()])
            scroll_view_to_region(view,target_line,self.last_pattern)
            return
        if not self.check_ext(view):
            return
        self.analyze(view)
        view.analyze_helper = self
        print (view)

        #view.add_regions('body',body_regions,icon='dot',scope="comment2")

    def test_region_str_is_file(self,region_str):
        return region_str.startswith('/Users') or region_str.startswith('C:\\')

    def on_click(self,point,href):
        print ("href: ",href)
        view = sublime.active_window().active_view()
        view.hide_popup()
        #view.analyze_helper.analyze()

        regions = view.get_regions('headers')
        target_region = None
        file_region = None
        file_name = None
        file_region_num = None
        for region_num,region in enumerate(regions):
            if region.b < point:
                target_region = region
            else:
                break
            region_str = view.substr(region)
            if self.test_region_str_is_file(region_str):
                file_region = region
                file_name = region_str[:3+region_str[3:].find(':')]
                file_region_num = region_num
        if href.startswith('vulnerable') or href.startswith('unvulnerable'):

            print ('target_region: ',target_region)
            view.run_command('edit',{'index':target_region.b,
                                     'insert_string':href})
            self.analyze(view)
        if href == 'all_unvulnerable':
            unvulnerable_regions = [file_region]
            for region in regions[file_region_num+1:]:
                region_str = view.substr(region)
                if self.test_region_str_is_file(region_str):
                    break
                unvulnerable_regions.append(region)
            for region in unvulnerable_regions[::-1]:
                view.run_command('edit',{'index':region.b,
                                         'insert_string':'unvulnerable'})
            self.analyze(view)
        elif href.startswith('show'):
            print(file_name)
            window = sublime.active_window()
            
            line = view.line(point)
            line_num = re.search(r'\s+(\d+)',view.substr(line)).group(1)
            line_num = int(line_num)
            print(line_num)

            existing_view = window.find_open_file(file_name)
            print ('existing view: ',existing_view)
            if existing_view is not None:
                target_line =get_region_for_show(existing_view,line_num)
                print ('target line:',target_line)
                #Найдем в целевой линии паттерн, чтобы его выделить.
                scroll_view_to_region(existing_view,target_line,self.last_pattern)
                window.focus_view(existing_view)
            else:
                print ('Opening new file')
                target_view = window.open_file(file_name)
                self.files_dict[file_name]=line_num
    


        if href.startswith('fold'):
            point = int(href[5:])
            print (point)

            print (regions)
            for region in regions:
                if (point >= region.a) and (point <=region.b):
                    print ('region to fold: ',region)
                    res = view.fold(region)
                    print ('folded: ',)


        #view.show_popup_menu(["fefefe","xxxx"],done_func)
        #sublime.Window.open_file(sublime.active_window(),'/etc/hosts')

    menu = ''' <a href='show'> Show</a><br>
<a href='vulnerable'>Vulnerable</a><br>
<a href='unvulnerable'>Unvulnerable</a><br>
<a href='all_unvulnerable'>All in file unvulnerable</a><br>
<a href='fold'>fold</a><br>
    '''


    def on_hover(self,view,point,hover_zone):
        if not self.check_ext(view):
            return
        #print (self)
        print ('point: ',point)
        print ('hover_zone ',hover_zone)
        callback = partial(self.on_click,point)
        if hover_zone == sublime.HOVER_TEXT:
            view.show_popup(self.menu,on_navigate=callback,flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,location=point)

    def onPreSave(self, view):
        print (view.fileName(), "is about to be saved")

    def onPostSave(self, view):
        print (view.fileName(), "just got saved")
        
    def onNew(self, view):
        print ("new file")

    def onModified(self, view):
        print (view.fileName(), "modified")

    def onActivated(self, view):
        print (view.fileName(), "is now the active view")

    def onClose(self, view):
        print (view.fileName(), "is no more")

    def onClone(self, view):
        print (view.fileName(), "just got cloned")
