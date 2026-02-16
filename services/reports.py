from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from models import Query, CableResponse
from sqlalchemy import func

def get_weekly_stats():
    """
    Agreguje statystyki z ostatnich 7 dni.
    Zwraca słownik z danymi do raportu.
    """
    now = datetime.now(ZoneInfo("Europe/Warsaw"))
    week_ago = now - timedelta(days=7)

    # Pobierz zapytania z ostatniego tygodnia
    queries = Query.query.filter(Query.date_submitted >= week_ago).all()

    total_queries = len(queries)
    sold_queries = 0
    lost_queries = 0
    pending_queries = 0
    unanswered_queries = []
    
    response_times = []

    for query in queries:
        # Status
        if query.is_won is True:
            sold_queries += 1
        elif query.is_won is False:
            lost_queries += 1
        else:
            pending_queries += 1

        # Sprawdź czy odpowiedziano na wszystkie kable
        if not query.is_all_responded():
            unanswered_queries.append(query)
        else:
            # Oblicz czas odpowiedzi dla zapytań zakończonych (lub częściowo)
            # Bierzemy pod uwagę czas do OSTATNIEJ odpowiedzi
            last_response_date = None
            if query.cables:
                for cable in query.cables:
                    if cable.response:
                        resp_date = cable.response.date_responded
                        if resp_date.tzinfo is None:
                            resp_date = resp_date.replace(tzinfo=ZoneInfo("Europe/Warsaw"))
                        
                        if last_response_date is None or resp_date > last_response_date:
                            last_response_date = resp_date
            
            if last_response_date:
                query_date = query.date_submitted
                if query_date.tzinfo is None:
                    query_date = query_date.replace(tzinfo=ZoneInfo("Europe/Warsaw"))
                    
                time_diff = (last_response_date - query_date).total_seconds() / 3600 # w godzinach
                response_times.append(time_diff)

    avg_response_time = 0
    if response_times:
        avg_response_time = sum(response_times) / len(response_times)

    return {
        'start_date': week_ago,
        'end_date': now,
        'total_queries': total_queries,
        'sold_queries': sold_queries,
        'lost_queries': lost_queries,
        'pending_queries': pending_queries,
        'unanswered_queries': unanswered_queries,
        'avg_response_time': round(avg_response_time, 2)
    }
