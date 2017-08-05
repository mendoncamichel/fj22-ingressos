package br.com.caelum.ingresso.validacao;

import java.time.LocalTime;
import java.util.List;
import java.util.Optional;

import br.com.caelum.ingresso.model.Sessao;

public class GerenciadorDeSessao {
	
	private List<Sessao> sessoesDaSala;
	
	public GerenciadorDeSessao(List<Sessao> sessoesDaSala){
		this.sessoesDaSala = sessoesDaSala;
	}
	
	public boolean cabe(final Sessao sessaoAtual){
	
		Optional<Boolean> optionalCabe = sessoesDaSala
										.stream()
										.map(sessaoExistente -> 
											horarioIsValido(sessaoExistente,sessaoAtual)
										)
										.reduce(Boolean::logicalAnd);
	return optionalCabe.orElse(true);
	}
	
	public boolean horarioIsValido(Sessao sessaoExistente, Sessao sessaoAtual){
		
		LocalTime horaroSessao = sessaoExistente.getHorario();
		LocalTime horarioAtual = sessaoAtual.getHorario();
		
		boolean ehAntes = horarioAtual.isBefore(horaroSessao);
		
		if(ehAntes){
			return sessaoAtual.getHorarioTermino().isBefore(horaroSessao);
		}else{
			return sessaoExistente.getHorarioTermino().isBefore(horarioAtual);
		}
	}
	
}
