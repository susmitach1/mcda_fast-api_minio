# from fastapi import APIRouter, HTTPException, status
# from src.database.models import Post
# from random import randrange

# router = APIRouter()

# my_list = [
#     {"title": "NAXA", "content": "Private company", "id": 1},
#     {"title": "IHRR", "content": "NGO company", "id": 2}
# ]

# @router.get("/post")
# def get_all_posts():
#     return {"data": my_list}

# @router.post("/posts", status_code=status.HTTP_201_CREATED)
# def create_post(post: Post):
#     post_dict = post.dict()
#     post_dict['id'] = randrange(0, 100000)
#     my_list.append(post_dict)
#     return {"data": post_dict}

# @router.get("/posts/latest")
# def get_latest_post():
#     post = my_list[-1]
#     return {"post_detail": post} 

# @router.get("/posts/{id}")
# def get_post_by_id(id: int):
#     post = find_post(id)
#     if not post:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
#     return {"post_detail": post}

# @router.delete("/posts/{id}", status_code=status.HTTP_204_NO_CONTENT)
# def delete_post(id: int):
#     indx = find_index_post(id)
#     if indx is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
#     my_list.pop(indx)
#     return {"message": f"Post with ID {id} successfully deleted"}

# @router.put("/posts/{id}")
# def update_post(id: int, post: Post):
#     indx = find_index_post(id)
#     if indx is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
#     post_dict = post.dict()
#     post_dict['id'] = id
#     my_list[indx] = post_dict
#     return {"message": f"Post with ID {id} successfully updated"}

# def find_post(id: int):
#     for post in my_list:
#         if post['id'] == id:
#             return post
#     return None

# def find_index_post(id: int):
#     for index, post in enumerate(my_list):
#         if post['id'] == id:
#             return index
#     return None