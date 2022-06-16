# 2022_II_ST_NPR
Repozytorium przeznaczone na przedmiot Narzędzia Przetwarzania Rozproszonego (NPR) na drugim stopniu studiów.

*Uruchomienie:* (testowe)  
```
$ 
pipenv run python Distr_Monit.py 
 
# Bardzo prosty przykład producenta konsumenta
pipenv run python prod.py 1 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772  
pipenv run python prod.py 0 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777  
pipenv run python prod.py 0 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776  
pipenv run python kons.py 0 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775   
pipenv run python kons.py 0 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774  
pipenv run python kons.py 0 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773  

# Przykład producenta konsumenta z możliwością czekania na pojawienie się produktu 
pipenv run python prod_wakeupall.py 1 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772  
pipenv run python prod_wakeupall.py 0 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777  
pipenv run python prod_wakeupall.py 0 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776  
pipenv run python kons_sleep.py 0 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775   
pipenv run python kons_sleep.py 0 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774  
pipenv run python kons_sleep.py 0 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773  

# Przykład producenta konsumenta z możliwością czekania na pojawienie się produktu, ale budzony jest tylko 1 proces 
pipenv run python prod_wakeup.py 1 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772  
pipenv run python prod_wakeup.py 0 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777  
pipenv run python prod_wakeup.py 0 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776  
pipenv run python kons_sleep.py 0 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775   
pipenv run python kons_sleep.py 0 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774  
pipenv run python kons_sleep.py 0 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773  

# Mniejsza ilość procesów
pipenv run python prod.py 1 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775
pipenv run python kons.py 0 127.0.0.1:7776 127.0.0.1:7777 127.0.0.1:7775
pipenv run python kons.py 0 127.0.0.1:7775 127.0.0.1:7777 127.0.0.1:7776
```
