#!-*- coding:utf-8 -*-

from __future__ import division
import cgi, math, os, datetime, logging
from time import strptime
import wsgiref.handlers

from google.appengine.ext import webapp, db
from google.appengine.api import images
from google.appengine.api import users
from google.appengine.ext.webapp import template

VALID_ADDRESS = [""]

#######################################
#
# Model
#
#######################################
class Tag(db.Model):
  TYPE_DATE = "date"
  TYPE_KEYWORD = "keyword"
  
  type = db.StringProperty()
  name = db.StringProperty()
  itemlist = db.StringListProperty()

  @property
  def Name(self):
    return "%s(%s)" %(self.name, len(self.itemlist))

class Article(db.Model):

  TYPE_BASIC = 1
  TYPE_BOOK = 2 
  
  createdate = db.DateProperty(auto_now=False)
  articletype = db.IntegerProperty()
  _title = db.StringProperty(multiline=False)
  comment = db.StringProperty(multiline=True)

  @property
  def title(self):
    if self._title is None:
      return ""
    return self._title

  @property
  def Comment(self):
    if self.comment is None:
      return ""
    return self.comment

  @property
  def Articletype(self):
    if self.articletype == Article.TYPE_BOOK:
      return "book"
    else:
      return ""

  @property
  def CreateDate(self):
    return self.createdate.strftime("%Y年%m月%d日");

class Photo(db.Model):
    """画像格納データストア"""
    article = db.ReferenceProperty(Article)
    photo = db.BlobProperty()
    filename = db.StringProperty(multiline=False)
    size = db.IntegerProperty()
    mimetype = db.StringProperty(multiline=False)
    comment = db.StringProperty(multiline=True)
    createdatetime = db.DateTimeProperty(auto_now_add=True)

    def getSize(self):
      return math.ceil(self.size / 1024);

    @property
    def Comment(self):
      if self.comment is None:
        return ""
      else:
        return self.comment.replace("\r\n", "<br />")

#####################################
#
# Business & Control
#
#####################################

class Rss(webapp.RequestHandler):
  def get(self):
    query = db.Query(Article)
    query = query.filter('articletype =', Article.TYPE_BASIC)
    query.order('-createdate')
    articles = query.fetch(limit=20)
    
    template_values = {
      'articles': articles,
      }

    path = os.path.join(os.path.dirname(__file__), 'template/default/rss.xml')
    self.response.headers['Content-Type'] = 'text/xml'
    self.response.out.write(template.render(path, template_values))    

class Home(webapp.RequestHandler):
  def get(self):
    datetagname = self.request.get('datetag')
    keywordtagname = self.request.get('keywordtag')
    articles = []
    photos = []
    title = ""
    #logging.info(datetagname)
    if datetagname != "":
      #logging.info("datatag")
      query = db.Query(Tag)
      query.filter('name =', datetagname)
      tags = query.fetch(limit=1)
      if len(tags) > 0: title = ' '+tags[0].name
      for k in tags[0].itemlist:
        article = db.get(k)
        if article.articletype == Article.TYPE_BASIC:
          articles.append(db.get(k))
    elif keywordtagname != "":
      query = db.Query(Tag)
      query.filter('name =', keywordtagname)
      tags = query.fetch(limit=1)
      if len(tags) > 0: title = ' '+tags[0].name
      for k in tags[0].itemlist:
        photos.append(db.get(k))
    else:
      query = db.Query(Article)
      query = query.filter('articletype =', Article.TYPE_BASIC)
      query.order('-createdate')
      articles = query.fetch(limit=10)

    #tag一覧取得
    query = db.Query(Tag).filter('type =', Tag.TYPE_DATE)
    query.order('name')
    datetags = query.fetch(limit=1000)

    query = db.Query(Tag).filter('type =', Tag.TYPE_KEYWORD)
    query.order('name')
    keywordtags = query.fetch(limit=1000)

    #book一覧取得
    query = db.Query(Article).filter('articletype =', Article.TYPE_BOOK)
    query.order('-createdate')
    books = query.fetch(limit=1000)
    
    template_values = {
      'title': title,
      'articles': articles,
      'books': books,
      'photos': photos,
      'datetags': datetags,
      'keywordtags': keywordtags,
      }

    path = os.path.join(os.path.dirname(__file__), 'template/default/index.html')
    self.response.out.write(template.render(path, template_values))    

class ArticleBasic(webapp.RequestHandler):
  def get(self):
    
    #記事取得
    articlekey = self.request.get('akey')
    articles = [db.get(articlekey)]
    
    #tag一覧取得
    query = db.Query(Tag).filter('type =', Tag.TYPE_DATE)
    query.order('name')
    datetags = query.fetch(limit=1000)

    query = db.Query(Tag).filter('type =', Tag.TYPE_KEYWORD)
    query.order('name')
    keywordtags = query.fetch(limit=1000)

    #book一覧取得
    query = db.Query(Article).filter('articletype =', Article.TYPE_BOOK)
    query.order('-createdate')
    books = query.fetch(limit=1000)
    
    title = ''
    if len(articles) > 0:
      title = ' '+articles[0].title
    
    template_values = {
      'title': title,
      'articles': articles,
      'books': books,
      'photos': [],
      'datetags': datetags,
      'keywordtags': keywordtags,
      }

    path = os.path.join(os.path.dirname(__file__), 'template/default/index.html')
    self.response.out.write(template.render(path, template_values))    

class Book(webapp.RequestHandler):
  def get(self):
    articlekey = self.request.get('akey')
    article = db.get(articlekey)

    template_values = {
      'title': ' BOOK ' + article.title,
      'article': article
      }

    path = os.path.join(os.path.dirname(__file__), 'template/default/book.html')
    self.response.out.write(template.render(path, template_values))    


def CheckAuth(self):
    user = users.get_current_user()
    logouturl = ""
    if user is not None:
        logging.debug(user.email())
    if not user:
        self.redirect(users.create_login_url(self.request.uri))
    elif user.email() not in VALID_ADDRESS:
        self.redirect(users.create_login_url(self.request.uri))

def SearchTag(tagname, tagtype):
  
  query = db.Query(Tag).filter('type =', tagtype)
  query.filter('name =', tagname)

  tag = Tag()
  tags = query.fetch(limit=1)
  # 既存のタグが存在すればそれを利用する
  # 1以上になることはない
  if len(tags) == 0:
    tag.name = tagname
    tag.type = tagtype
  else:
    tag = tags[0]

  return tag

def _GetFormatCreateDate(createdate):
  createdate = createdate.replace('-','/')
  createdate_tpl = strptime(createdate, "%Y/%m/%d")
  createdate = datetime.date(createdate_tpl[0],createdate_tpl[1],createdate_tpl[2])
  return createdate

class AdminArticle(webapp.RequestHandler):
  def get(self):
    CheckAuth(self)
    articles = Article.all().order('-createdate')
    template_values = {
      'articles': articles
      }
    path = os.path.join(os.path.dirname(__file__), 'template/admin/articlelist.html')
    self.response.out.write(template.render(path, template_values))    

  def post(self):
    CheckAuth(self)
    # Article追加
    article = Article()
    createdate = self.request.get('createdate').replace('-','/')
    createdate_tpl = strptime(createdate, "%Y/%m/%d")
    createdate = datetime.date(createdate_tpl[0],createdate_tpl[1],createdate_tpl[2])
    title = self.request.get('title')
    comment = self.request.get('comment')
    articletype = self.request.get('articletype')
    
    article.createdate = createdate
    article._title = title
    article.comment = comment
    if articletype != "":
      article.articletype = int(articletype)

    article.put()

    #DateTag追加
    tagname = createdate.strftime('%Y/%m')
    tag = SearchTag(tagname, Tag.TYPE_DATE)
    tag.itemlist.append(str(article.key()))
    tag.put()
      
    self.redirect("/admin/article")



class EditArticle(webapp.RequestHandler):
  def get(self):
    CheckAuth(self)
    articlekey = self.request.get("akey")
    article = db.get(str(articlekey))
    template_values = {
      "article": article
      }
    path = os.path.join(os.path.dirname(__file__), 'template/admin/articleedit.html')
    self.response.out.write(template.render(path, template_values))
    
  def post(self):
    CheckAuth(self)
    akey = self.request.get("akey")
    title = self.request.get("title")
    comment = self.request.get("comment")
    articletype = self.request.get("articletype")
    createdate = _GetFormatCreateDate(self.request.get("createdate"))

    article = db.get(akey)

    #DateTag修正
    if article.createdate != createdate:
      try:
        tagname = article.createdate.strftime('%Y/%m')
        tag = SearchTag(tagname, Tag.TYPE_DATE)
        tag.itemlist.remove(str(article.key()))
        if len(tag.itemlist) == 0:
          tag.delete()
        else:
          tag.put()
      except ValueError:
        pass
      tagname = createdate.strftime('%Y/%m')
      tag = SearchTag(tagname, Tag.TYPE_DATE)
      tag.itemlist.append(str(article.key()))
      tag.put()      

    article.createdate = createdate
    article._title = title
    article.comment = comment
    article.articletype = int(articletype)
    article.put()
    self.redirect("/admin/article")
                  
    
class DeleteArticle(webapp.RequestHandler):
  def get(self):
    CheckAuth(self)
    key = self.request.get("key")
    if key:
      item = db.get(key)

      try:
        #DateTag削除
        tagname = item.createdate.strftime('%Y/%m')
        query = db.Query(Tag)
        query.filter('name =', tagname)
        tags = query.fetch(limit=1)
        # 削除対象へのリファレンスを削除
        logging.info(len(tags[0].itemlist))
        tags[0].itemlist.remove(key)
        tags[0].put()
        logging.info(len(tags[0].itemlist))
        if len(tags[0].itemlist) == 0:
          # リファレンスがなくなったタグは削除
          logging.info("delete tag")
          tags[0].delete()
      except IndexError:
        pass
      except ValueError:
        pass
      # 最後に記事を削除          
      item.delete()
      
      

    self.redirect("/admin/article")

class AdminPhoto(webapp.RequestHandler):
  
    def get(self):
      CheckAuth(self)
      articlekey = self.request.get("akey")
      article = Article.get(articlekey)
      #back reference 遅いという話、問題が出たら対応。
      #サービス内容的に問題にはならないだろう。
      pics = article.photo_set

      template_values = {
        'pics': pics,
        'articlekey': articlekey
        }
      
      path = os.path.join(os.path.dirname(__file__), 'template/admin/photos.html')
      self.response.out.write(template.render(path, template_values))

    def post(self):
        CheckAuth(self)
        articlekey = self.request.get("akey")
        photo = self.request.get("photo")
        comment = self.request.get('comment')
        tagname = self.request.get('tag')
        template_values = {}

        article = Article.get(articlekey)

        if photo:
                    
            img = self.request.body_file.vars['photo']
            filename = img.filename
            
            bin = db.Blob(photo)
            img = images.Image(bin)
            img.resize(width=700, height=700)
            img.im_feeling_lucky()
            thumbnail = img.execute_transforms(output_encoding=images.JPEG)
            
            photo_upload = Photo()
            photo_upload.photo = thumbnail
            photo_upload.filename = filename
            photo_upload.size = len(thumbnail)
            photo_upload.mimetype = 'image/jpeg'
            photo_upload.comment = comment
            photo_upload.article = article
            photo_upload.put()

            #KeywordTag追加
            if (tagname != ""):
              tag = SearchTag(tagname, Tag.TYPE_KEYWORD)
              tag.itemlist.append(str(photo_upload.key()))
              tag.put()

            self.redirect("/admin/photo?akey="+articlekey)

class EditPhoto(webapp.RequestHandler):
  def get(self):
    CheckAuth(self)
    key = self.request.get("key")
    articlekey = self.request.get("akey")
    photo = db.get(key)
    template_values = {
      "photo": photo,
      "articlekey": articlekey
      }
    path = os.path.join(os.path.dirname(__file__), 'template/admin/photoedit.html')
    self.response.out.write(template.render(path, template_values))
    
  def post(self):
    CheckAuth(self)
    key = self.request.get("key")
    articlekey = self.request.get("akey")
    comment = self.request.get("comment")
    logging.debug(key)
    photo = db.get(key)
    photo.comment = comment
    photo.put()
    self.redirect("/admin/photo?akey="+articlekey)
    
class Delete(webapp.RequestHandler):
  def get(self):
    """画像削除処理"""
    CheckAuth(self)
    articlekey = self.request.get("akey")        
    key = self.request.get("key")
    if key:
      photo = Photo.get(key)

      try:
        #DateTag削除
        #タグを検索
        tags = Tag.all().filter("type =", Tag.TYPE_KEYWORD)
        target_tag = None
        for tag in tags:
          for k in tag.itemlist:
            if k == str(photo.key()):
              # 対象のタグを発見
              logging.info("find")
              target_tag = tag
              break
            
        if target_tag is not None:
          #削除対象の画像へのリファレンスを削除
          target_tag.itemlist.remove(str(photo.key()))
          target_tag.put()

          if len(target_tag.itemlist) == 0:
            # リファレンスがなくなったタグは削除
            logging.info("delete tag")
            target_tag.delete()

      except IndexError:
        logging.info("delete photo index error")
      except ValueError:
        logging.info("delete photo value error")

      photo.delete()

    self.redirect("/admin/photo?akey="+articlekey)

class Img(webapp.RequestHandler):

    def get(self,photoid):
        """画像出力処理"""
        img = Photo.get(photoid)
        if img:
            photo = img.photo
            mimetype = img.mimetype
            self.response.headers['Content-Type'] = str(mimetype)
            self.response.out.write(photo)
            return
        else:
            self.error(404)
            return self.response.out.write('404 not found')
          
def main():
    application = webapp.WSGIApplication(
                                        [
                                        ('/', Home),
                                        ('/article', ArticleBasic),
                                        ('/book', Book),
                                        ('/admin/article', AdminArticle),
                                        ('/admin/photo', AdminPhoto),
                                        ('/admin/photo/edit', EditPhoto),
                                        ('/admin/article/edit', EditArticle),                                        
                                        ('/admin/article/delete', DeleteArticle),
                                        ('/delete', Delete),
                                        ('/img/([^/]+)', Img),
                                        ('/rss', Rss),
                                        ],
                                        debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()
