# 2022_II_ST_NPR
Repozytorium przeznaczone na przedmiot Narzędzia Przetwarzania Rozproszonego (NPR) na drugim stopniu studiów.

*Uruchomienie:* (testowe)  
```
$ 
pipenv run python Distr_Monit.py  
pipenv run python prod.py 1 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772  
pipenv run python prod.py 0 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777  
pipenv run python prod.py 0 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776  
pipenv run python kons.py 0 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775   
pipenv run python kons.py 0 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774  
pipenv run python kons.py 0 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773  

pipenv run python prod.py 1 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775
pipenv run python kons.py 0 127.0.0.1:7776 127.0.0.1:7777 127.0.0.1:7775
pipenv run python kons.py 0 127.0.0.1:7775 127.0.0.1:7777 127.0.0.1:7776
```
